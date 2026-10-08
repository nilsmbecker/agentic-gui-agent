"""Structured feedback: did the last action visibly change the screen? No emulator needed."""

import numpy as np

from gui_agent.feedback import changed_fraction, no_effect_hint

H, W = 2400, 1080


def _screen():
    return np.full((H, W, 3), 230, dtype=np.uint8)


def test_identical_screens_unchanged():
    assert changed_fraction(_screen(), _screen()) == 0.0


def test_status_bar_is_ignored():
    after = _screen()
    after[:150] = 0  # clock / pointer overlay
    assert changed_fraction(_screen(), after) == 0.0


def test_small_icon_change_is_below_threshold_but_text_is_not():
    icon = _screen()
    icon[400:416, 900:915] = 90  # ~240 px, like Markor's save icon turning grey
    text = _screen()
    text[300:360, 40:1000] = 20  # a typed line
    assert no_effect_hint({"action": "CLICK"}, changed_fraction(_screen(), icon))
    assert no_effect_hint({"action": "TYPE"}, changed_fraction(_screen(), text)) is None


def test_no_feedback_for_actions_that_should_not_change_the_screen():
    assert no_effect_hint({"action": "WAIT"}, 0.0) is None
    assert no_effect_hint({"action": "COMPLETE"}, 0.0) is None
