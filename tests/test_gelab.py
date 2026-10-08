"""Screenshot encoding sent to the model. Runs without emulator or model."""

import base64
import io

import numpy as np
from PIL import Image

from gui_agent.gelab import HINTS, Parser0920Summary, pixels_to_data_url, with_hints

SCREEN = np.zeros((2400, 1080, 3), dtype=np.uint8)  # Pixel 6, height x width


def _decode(url: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1])))


def test_resized_like_gelab_upstream():
    url = pixels_to_data_url(SCREEN, 728)
    assert url.startswith("data:image/jpeg;base64,")
    assert _decode(url).size == (728, 728)


def test_full_resolution_png():
    url = pixels_to_data_url(SCREEN, 0)
    assert url.startswith("data:image/png;base64,")
    assert _decode(url).size == (1080, 2400)


def _prompt_text(**kwargs) -> str:
    env = {"image": pixels_to_data_url(SCREEN, 728), "user_comment": ""}
    messages = Parser0920Summary().env2messages4ask(environments=[env], actions=[], **kwargs)
    return " ".join(c["text"] for c in messages[0]["content"] if c["type"] == "text")


def test_upstream_drops_hints_argument():
    # Documents the upstream quirk that with_hints() works around.
    assert HINTS[0] not in _prompt_text(task="t", hints=HINTS)


def test_hints_reach_the_prompt_via_task_text():
    assert "### HINT" in _prompt_text(task=with_hints("Turn wifi on.")) and HINTS[0] in _prompt_text(
        task=with_hints("Turn wifi on.")
    )
