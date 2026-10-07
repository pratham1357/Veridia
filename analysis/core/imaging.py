"""Image decoding/encoding helpers shared by the analysis modules.

All pixel-domain algorithms in VERIDIA operate on an 8-bit RGB array of shape
(height, width, 3). Images in other modes are converted to RGB on decode (an
alpha channel, if present, is discarded). Outputs are always written as PNG,
because lossy formats would destroy LSB-domain data.
"""

import io

import numpy as np
from PIL import Image


class ImageDecodeError(ValueError):
    """The bytes could not be decoded as a supported image."""


def probe(data: bytes) -> tuple[str, int, int]:
    """Return (format, width, height) from the image header without decoding pixels."""
    try:
        with Image.open(io.BytesIO(data)) as img:
            return img.format or "UNKNOWN", img.width, img.height
    except Exception as exc:  # untrusted input: Pillow can raise many types
        raise ImageDecodeError("File could not be read as an image.") from exc


def decode_rgb(data: bytes) -> np.ndarray:
    """Fully decode to a writable uint8 RGB array (H, W, 3)."""
    try:
        with Image.open(io.BytesIO(data)) as img:
            return np.array(img.convert("RGB"), dtype=np.uint8)
    except Exception as exc:
        raise ImageDecodeError("File could not be decoded as an image.") from exc


def encode_png(pixels: np.ndarray) -> bytes:
    """Encode an RGB (H, W, 3) or grayscale (H, W) uint8 array as lossless PNG."""
    buf = io.BytesIO()
    Image.fromarray(pixels).save(buf, format="PNG")
    return buf.getvalue()
