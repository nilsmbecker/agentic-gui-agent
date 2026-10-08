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

__all__ = ["Parser0920Summary", "parse_action", "pixels_to_data_url"]


def parse_action(parser: Parser0920Summary, text: str) -> dict:
    """Model reply -> validated GELab action dict. Raises AssertionError/ValueError/KeyError if invalid.

    Upstream `action2action` validates and normalizes, but its copy drops TYPE's `point`
    (needed to focus the field before typing) and ABORT's `value` (the reason). Put them back.
    """
    raw = parser.str2action(text)
    raw.setdefault("explain", "")
    action = parser.action2action(raw)
    for key in ("point", "value"):
        if key in raw:
            action.setdefault(key, raw[key])
    return action


def pixels_to_data_url(pixels: np.ndarray, size: int = 0) -> str:
    """RGB screenshot array -> base64 data URL for the model.

    size > 0: squash to size x size and encode as JPEG q85, exactly like upstream's
    `tools/image_tools.py:make_b64_url` (their deployment uses 728x728). Aspect ratio is not kept;
    that is fine because GELab answers in 0-1000 coordinates relative to the image.
    size == 0: the full-resolution screenshot as PNG.
    """
    img = Image.fromarray(pixels.astype("uint8")).convert("RGB")
    buf = io.BytesIO()
    if size:
        img.resize((size, size)).save(buf, format="JPEG", quality=85)
        mime = "jpeg"
    else:
        img.save(buf, format="PNG")
        mime = "png"
    return f"data:image/{mime};base64," + base64.b64encode(buf.getvalue()).decode()
