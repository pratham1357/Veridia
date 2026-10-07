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
