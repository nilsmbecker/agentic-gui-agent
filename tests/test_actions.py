"""GELab -> AndroidWorld action mapping. Runs without emulator or model."""

from types import SimpleNamespace

import pytest

from gui_agent.actions import denormalize, element_at, text_field_target, to_android_actions

W, H = 1080, 2400  # Pixel 6


def test_denormalize_scales_and_clamps():
    assert denormalize([500, 500], W, H) == (540, 1200)
    assert denormalize([1000, 1000], W, H) == (W - 1, H - 1)
    assert denormalize([0, 0], W, H) == (0, 0)


def test_click():
    t = to_android_actions({"action": "CLICK", "point": [500, 250]}, W, H)
    assert t.json_actions == [{"action_type": "click", "x": 540, "y": 600}]
    assert not t.done


def test_type_focuses_point_and_clears():
    t = to_android_actions({"action": "TYPE", "value": "hello", "point": [100, 100]}, W, H)
    assert t.json_actions == [
        {"action_type": "input_text", "text": "hello", "clear_text": True, "x": 108, "y": 240}
    ]


def test_slide_becomes_exact_swipe():
    t = to_android_actions({"action": "SLIDE", "point1": [500, 800], "point2": [500, 200]}, W, H)
    assert t.json_actions == []
    assert (t.swipe.y1, t.swipe.y2) == (1920, 480)


def test_complete_answers_then_ends():
    t = to_android_actions({"action": "COMPLETE", "return": "42"}, W, H)
    assert t.done
    assert t.json_actions == [
        {"action_type": "answer", "text": "42"},
        {"action_type": "status", "goal_status": "complete"},
    ]


@pytest.mark.parametrize("kind", ["INFO", "NONSENSE"])
def test_unexecutable_actions_do_nothing_but_note(kind):
    t = to_android_actions({"action": kind, "value": "?"}, W, H)
    assert t.json_actions == [] and t.swipe is None and not t.done and t.note


def test_gelab_parser_roundtrip():
    gelab = pytest.importorskip("gui_agent.gelab")
    raw = "<THINK> open settings </THINK>\nexplain:tap gear\taction:CLICK\tpoint:120,880\tsummary:opened"
    parsed = gelab.Parser0920Summary().str2action(raw)
    assert parsed["action"] == "CLICK" and parsed["point"] == [120, 880]
    assert to_android_actions(parsed, W, H).json_actions[0]["action_type"] == "click"


def test_parse_action_keeps_type_point_and_abort_reason():
    # The agent's real path: upstream action2action() drops TYPE's point and ABORT's value.
    gelab = pytest.importorskip("gui_agent.gelab")
    parser = gelab.Parser0920Summary()

    typed = gelab.parse_action(parser, "<THINK> t </THINK>\nexplain:e\taction:TYPE\tvalue:Ada\tpoint:500,300")
    assert to_android_actions(typed, W, H).json_actions == [
        {"action_type": "input_text", "text": "Ada", "clear_text": True, "x": 540, "y": 720}
    ]

    aborted = gelab.parse_action(parser, "<THINK> t </THINK>\nexplain:e\taction:ABORT\tvalue:no such app")
    assert to_android_actions(aborted, W, H).note == "ABORT: no such app"


def _el(x0, y0, x1, y1, editable=True, focused=False, visible=True):
    box = SimpleNamespace(center=((x0 + x1) / 2, (y0 + y1) / 2), area=(x1 - x0) * (y1 - y0))
    return SimpleNamespace(is_editable=editable, is_focused=focused, is_visible=visible, bbox_pixels=box)


def test_text_field_target_prefers_focused_field():
    big, small_focused = _el(0, 300, 1080, 2000), _el(80, 500, 640, 560, focused=True)
    assert text_field_target([big, small_focused]) == (360, 530)


def test_text_field_target_falls_back_to_largest_editable():
    # Markor's editor after "OK": keyboard is up, but no field reports focus.
    title, body = _el(0, 0, 1080, 200), _el(0, 300, 1080, 2000)
    button = _el(900, 2100, 1080, 2200, editable=False)
    assert text_field_target([title, body, button]) == (540, 1150)


def test_text_field_target_none_without_editable_fields():
    assert text_field_target([_el(0, 0, 10, 10, editable=False), _el(0, 0, 10, 10, visible=False)]) is None


def _labelled(desc, x0, y0, x1, y1, enabled=True):
    box = SimpleNamespace(x_min=x0, y_min=y0, x_max=x1, y_max=y1, area=(x1 - x0) * (y1 - y0))
    return SimpleNamespace(content_description=desc, text=None, is_enabled=enabled, bbox_pixels=box)


def test_element_at_picks_smallest_labelled_element_under_tap():
    # Markor toolbar after saving: the Save icon is disabled (from the 2026-10-08 probe).
    toolbar = _labelled("Toolbar", 0, 138, 1080, 264)
    save = _labelled("Save", 765, 138, 870, 264, enabled=False)
    assert element_at([toolbar, save], 810, 197) == ("Save", False)
    assert element_at([toolbar, save], 100, 900) is None
