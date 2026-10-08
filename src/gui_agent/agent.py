"""GELab-Zero agent for AndroidWorld: one `step()` = observe -> decide -> act -> report done.

This is the project's required shape (see docs/PLAN.md). Everything the agent
saw and did in a step is returned in `AgentInteractionResult.data` and written
to the trajectory log, so every failure can be traced back to a concrete step.
"""

from __future__ import annotations

from android_world.agents.base_agent import AgentInteractionResult, EnvironmentInteractingAgent
from android_world.env import adb_utils, interface, json_action

from gui_agent.actions import is_repeat, text_field_target, to_android_actions
from gui_agent.config import Settings
from gui_agent.gelab import Parser0920Summary, parse_action, pixels_to_data_url
from gui_agent.llm_client import LLMClient
from gui_agent.trajectory import TrajectoryLogger

# Bounded recovery (D4): give up after this many failed steps in a row
# (unparseable reply or model/server error).
MAX_CONSECUTIVE_FAILURES = 3
# Loop detection (D4): stop when the model emits the identical action this many times in a row.
MAX_REPEATED_ACTIONS = 3


class GelabAgent(EnvironmentInteractingAgent):
    def __init__(
        self,
        env: interface.AsyncEnv,
        settings: Settings,
        llm: LLMClient | None = None,
        logger: TrajectoryLogger | None = None,
        name: str = "gelab_zero",
    ):
        super().__init__(env, name, transition_pause=settings.transition_pause_s)
        self.settings = settings
        self.llm = llm or LLMClient(settings)
        self.logger = logger
        self.parser = Parser0920Summary()
        self._reset_history()

    def _reset_history(self) -> None:
        # GELab's prompt builder needs len(environments) == len(actions) + 1.
        self._environments: list[dict] = []
        self._actions: list[dict] = []
        self._step = 0
        self._failures = 0
        self._repeats = 0

    def reset(self, go_home: bool = False) -> None:
        super().reset(go_home)
        self._reset_history()

    def step(self, goal: str) -> AgentInteractionResult:
        # 1. Observe
        state = self.get_post_transition_state()
        pixels = state.pixels
        height, width = pixels.shape[:2]
        size = self.settings.llm_image_size
        if self._environments:
            self._environments[-1]["image"] = None  # only the newest screenshot is sent
        self._environments.append({"image": pixels_to_data_url(pixels, size), "user_comment": ""})

        # 2. Decide
        messages = self.parser.env2messages4ask(
            task=goal, environments=self._environments, actions=self._actions
        )
        # step_NNN.png keeps the real screen; model_image is what the model actually saw.
        record: dict = {"goal": goal, "model_image": [size, size] if size else [width, height]}
        try:
            reply = self.llm.chat(messages)
        except (RuntimeError, OSError, ValueError, KeyError) as e:  # OSError covers URLError/timeouts
            record["llm_error"] = f"{type(e).__name__}: {e}"
            return self._fail(record, pixels, "llm_errors")
        record.update(model_output=reply.text, latency_s=round(reply.latency_s, 2), usage=reply.usage)

        try:
            parsed = parse_action(self.parser, reply.text)
        except (AssertionError, ValueError, KeyError) as e:
            record["parse_error"] = str(e)
            return self._fail(record, pixels, "parse_errors")

        self._failures = 0
        prev = self._actions[-1] if self._actions else None
        self._repeats = self._repeats + 1 if is_repeat(prev, parsed) else 1
        self._actions.append(parsed)
        translation = to_android_actions(parsed, width, height)
        for kwargs in translation.json_actions:
            if kwargs["action_type"] == "input_text" and "x" not in kwargs:
                # GELab often sends TYPE without a point; tap a text field first so the text arrives.
                target = text_field_target(state.ui_elements)
                if target:
                    kwargs["x"], kwargs["y"] = target
                    record["focus_tap"] = list(target)
        record.update(
            action=dict(parsed),
            executed=translation.json_actions,
            swipe=vars(translation.swipe) if translation.swipe else None,
            note=translation.note,
            repeats=self._repeats,
        )
        if self._repeats >= MAX_REPEATED_ACTIONS:
            # Don't execute it a 3rd time: end the episode with evidence for the `loop` tag.
            record.update(loop_detected=True, stop_reason="loop")
            return self._finish(record, pixels, True)

        # 3. Act
        try:
            for kwargs in translation.json_actions:
                self.env.execute_action(json_action.JSONAction(**kwargs))
            if translation.swipe:
                s = translation.swipe
                cmd = adb_utils.generate_swipe_command(s.x1, s.y1, s.x2, s.y2, s.duration_ms)
                adb_utils.issue_generic_request(cmd, self.env.controller)
        except Exception as e:  # noqa: BLE001 - surface every execution error in the log
            record["execution_error"] = f"{type(e).__name__}: {e}"

        # 4. Report done
        if translation.done:
            record["stop_reason"] = (parsed.get("action") or "").lower()  # "complete" or "abort"
        return self._finish(record, pixels, translation.done)

    def _fail(self, record: dict, pixels, reason: str) -> AgentInteractionResult:
        """A step that produced no executable action; ends the episode after too many in a row."""
        self._environments.pop()  # keep GELab's invariant: len(environments) == len(actions) + 1
        self._failures += 1
        record["consecutive_failures"] = self._failures
        done = self._failures >= MAX_CONSECUTIVE_FAILURES
        if done:
            record["stop_reason"] = reason
        return self._finish(record, pixels, done)

    def _finish(self, record: dict, pixels, done: bool) -> AgentInteractionResult:
        record["done"] = done
        if self.logger:
            self.logger.log_step(self._step, record, pixels)
        self._step += 1
        return AgentInteractionResult(done=done, data=record)
