"""Thin bridge to GELab-Zero's own prompt builder and output parser.

We reuse upstream's `Parser0920Summary` (third_party/gelab-zero) instead of
copying it, so the prompt stays exactly what the model was trained on.
"""

from __future__ import annotations

import base64
import io
import sys

import numpy as np
from PIL import Image

from gui_agent.config import REPO_ROOT

_GELAB_DIR = REPO_ROOT / "third_party" / "gelab-zero"
if str(_GELAB_DIR) not in sys.path:
    sys.path.insert(0, str(_GELAB_DIR))

from copilot_tools.parser_0920_summary import Parser0920Summary  # noqa: E402

__all__ = ["Parser0920Summary", "pixels_to_data_url"]


def pixels_to_data_url(pixels: np.ndarray, max_side: int | None = None) -> str:
    """RGB screenshot array -> base64 PNG data URL (optionally downscaled)."""
    img = Image.fromarray(pixels.astype("uint8"))
    if max_side and max(img.size) > max_side:
        img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
