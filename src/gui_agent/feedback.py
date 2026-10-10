"""Structured feedback: tell the model when its last action had no visible effect.

In MarkorCreateNote the note was saved correctly, but the only visible effect was the save icon
turning grey (~240 px), which the 4B model never noticed. It kept tapping save until the loop
guard stopped it, without ever saying COMPLETE. See docs/analysis/MarkorCreateNote_investigation.md.
"""

from __future__ import annotations

import numpy as np

# The top of the screen changes on its own: status bar clock and AndroidWorld's
# pointer-location overlay (the "P: 0 / 1  dX ..." bar).
TOP_CROP = 0.08
# A pixel counts as changed if any RGB channel moved by more than this.
PIXEL_DELTA = 20
# Below this fraction of changed pixels, an action had "almost no visible effect".
# Measured on Pixel 6 screenshots: typing one line ~2.5 %, save icon greying out ~0.01 %,
# blinking cursor ~0.01 %.
MIN_CHANGE = 0.001
# Actions that are not expected to change the screen.
_NO_FEEDBACK = {"WAIT", "COMPLETE", "ABORT", "INFO"}


def changed_fraction(before: np.ndarray, after: np.ndarray) -> float:
    """Fraction of pixels (below the status bar) that differ between two RGB screenshots."""
    if before.shape != after.shape:
        return 1.0
    y0 = int(before.shape[0] * TOP_CROP)
    diff = np.abs(before[y0:].astype(np.int16) - after[y0:].astype(np.int16)).max(axis=-1)
    return float((diff > PIXEL_DELTA).mean())


def no_effect_hint(
    last_action: dict, fraction: float, times: int = 1, element: tuple[str, bool] | None = None
) -> str | None:
    """Hint for the next prompt if `last_action` barely changed the screen, else None.

    `times`: how often this same action in a row had no visible effect. A repeated, identical
    message was ignored, so the hint names the action and gets firmer with every repeat.
    `element`: (label, enabled) of the tapped element after the tap. "No visible change" alone
    was read as "it failed", so the hint also says when the target is disabled.
    """
    kind = (last_action.get("action") or "").upper()
    if kind in _NO_FEEDBACK or fraction >= MIN_CHANGE:
        return None
    point = last_action.get("point")
    where = f" at {point[0]},{point[1]}" if point else ""
    text = f"Your last action ({kind}{where}) did not visibly change the screen."
    if element and not element[1]:
        text += (
            f" The element you tapped ('{element[0]}') is disabled (greyed out),"
            " so tapping it again does nothing."
        )
    if times > 1:
        text += (
            f" You have now done this {times} times without any visible effect; doing it again will not help."
        )
    return text + " If the task is already complete, output COMPLETE now; otherwise try a different action."
