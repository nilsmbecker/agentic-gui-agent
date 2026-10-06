"""GELab-Zero agent for AndroidWorld: one `step()` = observe -> decide -> act -> report done.

This is the project's required shape (see docs/PLAN.md). Everything the agent
saw and did in a step is returned in `AgentInteractionResult.data` and written
to the trajectory log, so every failure can be traced back to a concrete step.
"""

from __future__ import annotations

from android_world.agents.base_agent import AgentInteractionResult, EnvironmentInteractingAgent
from android_world.env import adb_utils, interface, json_action

from gui_agent.actions import to_android_actions
from gui_agent.config import Settings
from gui_agent.gelab import Parser0920Summary, pixels_to_data_url
from gui_agent.llm_client import LLMClient
from gui_agent.trajectory import TrajectoryLogger

# Bounded recovery (D4): give up after this many unparseable model replies in a row.
MAX_CONSECUTIVE_PARSE_FAILURES = 3


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
        self._parse_failures = 0

    def reset(self, go_home: bool = False) -> None:
        super().reset(go_home)
        self._reset_history()

    def step(self, goal: str) -> AgentInteractionResult:
        # 1. Observe
        state = self.get_post_transition_state()
        pixels = state.pixels
        height, width = pixels.shape[:2]
        if self._environments:
            self._environments[-1]["image"] = None  # only the newest screenshot is sent
        self._environments.append({"image": pixels_to_data_url(pixels), "user_comment": ""})

        # 2. Decide
        messages = self.parser.env2messages4ask(
            task=goal, environments=self._environments, actions=self._actions
        )
        reply = self.llm.chat(messages)
        record: dict = {
            "goal": goal,
            "model_output": reply.text,
            "latency_s": round(reply.latency_s, 2),
            "usage": reply.usage,
        }

        try:
            parsed = self.parser.str2action(reply.text)
            parsed.setdefault("explain", "")
            parsed = self.parser.action2action(parsed)  # validates required fields
        except (AssertionError, ValueError, KeyError) as e:
            self._environments.pop()  # keep the env/action lists aligned
            self._parse_failures += 1
            record.update(parse_error=str(e), parse_failures=self._parse_failures)
            done = self._parse_failures >= MAX_CONSECUTIVE_PARSE_FAILURES
            return self._finish(record, pixels, done)

        self._parse_failures = 0
        self._actions.append(parsed)
        translation = to_android_actions(parsed, width, height)
        record.update(
            action=dict(parsed),
            executed=translation.json_actions,
            swipe=vars(translation.swipe) if translation.swipe else None,
            note=translation.note,
        )

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
        return self._finish(record, pixels, translation.done)

    def _finish(self, record: dict, pixels, done: bool) -> AgentInteractionResult:
        record["done"] = done
        if self.logger:
            self.logger.log_step(self._step, record, pixels)
        self._step += 1
        return AgentInteractionResult(done=done, data=record)
