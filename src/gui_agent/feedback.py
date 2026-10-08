"""Structured feedback (D4): tell the model when its last action had no visible effect.

Added after MarkorCreateNote round 1 (2026-10-08): the note was saved correctly, but the only
visible effect was Markor's save icon turning grey (~240 px), which the 4B model never noticed.
It kept tapping save until the loop guard stopped it, without ever saying COMPLETE.
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


def no_effect_hint(last_action: dict, fraction: float) -> str | None:
    """Hint for the next prompt if `last_action` barely changed the screen, else None."""
    kind = (last_action.get("action") or "").upper()
    if kind in _NO_FEEDBACK or fraction >= MIN_CHANGE:
        return None
    return (
        f"Your last action ({kind}) did not visibly change the screen."
        " If the task is already complete, output COMPLETE now; otherwise try a different action."
    )
