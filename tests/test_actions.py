"""GELab -> AndroidWorld action mapping. Runs without emulator or model."""

import pytest

from gui_agent.actions import denormalize, to_android_actions

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
