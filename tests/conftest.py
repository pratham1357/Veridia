import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from analysis.core import encode_png
from app.main import app


@pytest.fixture
def pixels() -> np.ndarray:
    """Deterministic 64x64 RGB test image."""
    return np.random.default_rng(42).integers(0, 256, (64, 64, 3), dtype=np.uint8)


def natural_image(h: int = 256, w: int = 256, seed: int = 7) -> np.ndarray:
    """Deterministic synthetic 'natural' image: smooth gradients and waves, a hard-edged disc, mild noise.

    Uniform random noise is a poor stand-in for photographs in steganalysis (its LSB
    pairs are already equalised), so detector tests use this instead.
    """
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w] / max(h, w)
    base = 120 + 60 * np.sin(2 * np.pi * (1.3 * x + 0.4 * y)) + 40 * np.cos(2 * np.pi * 2.1 * y * x)
    img = np.stack([base, base * 0.8 + 120 * x, 200 - base * 0.5 + 20 * y], -1)
    yy, xx = np.mgrid[0:h, 0:w]
    img[((yy - h * 0.6) ** 2 + (xx - w * 0.3) ** 2) < (h * 0.2) ** 2] = [220, 60, 50]
    img += rng.normal(0, 3, img.shape)
    return np.clip(np.rint(img), 0, 255).astype(np.uint8)


@pytest.fixture
def natural() -> np.ndarray:
    return natural_image()


@pytest.fixture
def natural_png(natural: np.ndarray) -> bytes:
    return encode_png(natural)


@pytest.fixture
def png_bytes(pixels: np.ndarray) -> bytes:
    return encode_png(pixels)


@pytest.fixture
def jpeg_with_exif(pixels: np.ndarray) -> bytes:
    exif = Image.Exif()
    exif[0x010F] = "VeridiaCam"  # Make
    buf = io.BytesIO()
    Image.fromarray(pixels).save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
