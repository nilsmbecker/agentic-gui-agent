"""Screenshot encoding sent to the model. Runs without emulator or model."""

import base64
import io

import numpy as np
from PIL import Image

from gui_agent.gelab import pixels_to_data_url

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
