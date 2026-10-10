"""Translate GELab-Zero actions into AndroidWorld actions.

GELab-Zero speaks its own action space (CLICK, TYPE, SLIDE, AWAKE, COMPLETE, ...)
with coordinates normalized to 0-1000. AndroidWorld executes `JSONAction`s in
screen pixels. This module is the only place where that mapping lives.

Kept free of android_world imports so it can be unit-tested without an emulator:
`to_android_actions` returns plain dicts (JSONAction kwargs) plus an optional
raw swipe, and the agent builds the real objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field

GELAB_COORD_MAX = 1000


@dataclass
class Swipe:
    """Exact finger swipe in pixels. AndroidWorld's JSONAction only knows directions."""

    x1: int
    y1: int
    x2: int
    y2: int
    duration_ms: int = 500


@dataclass
class Translation:
    """What to execute for one GELab action, in order."""

    json_actions: list[dict] = field(default_factory=list)
    swipe: Swipe | None = None
    done: bool = False  # agent believes the episode is over
    note: str = ""  # anything worth logging (e.g. unsupported action)


def denormalize(point: list[int] | tuple[int, int], screen_w: int, screen_h: int) -> tuple[int, int]:
    """GELab 0-1000 coordinates -> pixel coordinates, clamped to the screen."""
    x, y = point
    px = round(x / GELAB_COORD_MAX * screen_w)
    py = round(y / GELAB_COORD_MAX * screen_h)
    return min(max(px, 0), screen_w - 1), min(max(py, 0), screen_h - 1)


# Actions that are legitimately repeated (scrolling a long list, waiting for a load).
_REPEATABLE = {"SLIDE", "WAIT"}
_IDENTITY_KEYS = ("action", "point", "point1", "point2", "value")


def is_repeat(prev: dict | None, action: dict) -> bool:
    """True if `action` is exactly the previous action again (used for loop detection)."""
    if prev is None or (action.get("action") or "").upper() in _REPEATABLE:
        return False
    return all(prev.get(k) == action.get(k) for k in _IDENTITY_KEYS)


def text_field_target(ui_elements) -> tuple[int, int] | None:
    """Where to tap so that a TYPE without a point lands in a text field.

    `adb input text` only reaches a view that holds input focus. Markor's editor can show the
    keyboard without holding it, and then the text silently disappears (MarkorCreateNote).
    Prefer the focused editable field, else the largest visible one.
    `ui_elements` are android_world UIElements (duck-typed, so this stays testable).
    """
    editable = [
        e for e in ui_elements if e.is_editable and e.is_visible is not False and e.bbox_pixels is not None
    ]
    if not editable:
        return None
    target = next((e for e in editable if e.is_focused), None) or max(
        editable, key=lambda e: e.bbox_pixels.area
    )
    x, y = target.bbox_pixels.center
    return int(x), int(y)


def element_at(ui_elements, x: int, y: int) -> tuple[str, bool] | None:
    """(label, enabled) of the smallest labelled element under pixel (x, y), else None.

    Used for feedback after a tap: Markor's save icon turning grey after saving is a ~240 px
    change the model can't see, but the accessibility tree reports it as enabled=False.
    """
    hits = [
        e
        for e in ui_elements
        if e.bbox_pixels is not None
        and (e.content_description or e.text)
        and e.bbox_pixels.x_min <= x <= e.bbox_pixels.x_max
        and e.bbox_pixels.y_min <= y <= e.bbox_pixels.y_max
    ]
    if not hits:
        return None
    e = min(hits, key=lambda e: e.bbox_pixels.area)
    return (e.content_description or e.text), e.is_enabled is not False


def to_android_actions(action: dict, screen_w: int, screen_h: int) -> Translation:
    """Map one parsed GELab action dict (from Parser0920Summary.str2action) to AndroidWorld."""
    kind = (action.get("action") or action.get("action_type") or "").upper()

    if kind in ("CLICK", "LONGPRESS"):
        x, y = denormalize(action["point"], screen_w, screen_h)
        return Translation([{"action_type": "click" if kind == "CLICK" else "long_press", "x": x, "y": y}])

    if kind == "TYPE":
        act = {"action_type": "input_text", "text": action.get("value", ""), "clear_text": True}
        if "point" in action:
            act["x"], act["y"] = denormalize(action["point"], screen_w, screen_h)
        return Translation([act])

    if kind == "SLIDE":
        x1, y1 = denormalize(action["point1"], screen_w, screen_h)
        x2, y2 = denormalize(action["point2"], screen_w, screen_h)
        return Translation(swipe=Swipe(x1, y1, x2, y2))

    if kind == "AWAKE":
        return Translation([{"action_type": "open_app", "app_name": action.get("value", "")}])

    if kind == "WAIT":
        return Translation([{"action_type": "wait"}])

    if kind == "COMPLETE":
        # `answer` fills env.interaction_cache, which information-retrieval tasks grade on.
        answer = action.get("return", "")
        acts = [{"action_type": "answer", "text": answer}] if answer else []
        acts.append({"action_type": "status", "goal_status": "complete"})
        return Translation(acts, done=True)

    if kind == "ABORT":
        return Translation(
            [{"action_type": "status", "goal_status": "infeasible"}],
            done=True,
            note=f"ABORT: {action.get('value', '')}",
        )

    if kind == "INFO":
        # No human in the loop during benchmark runs: the question goes unanswered.
        return Translation(note=f"INFO (unanswered, no user in loop): {action.get('value', '')}")

    return Translation(note=f"unknown action type {kind!r}: {action}")
