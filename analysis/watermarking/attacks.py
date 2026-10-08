"""Controlled image modifications ("attacks") for watermark robustness experiments.

Every attack takes and returns an 8-bit RGB array of the same shape, so the
watermark detector sees the original geometry. Random attacks use a fixed seed,
so experiments are reproducible.
"""

import io
from dataclasses import dataclass
from typing import Callable

import numpy as np
from PIL import Image


def jpeg(pixels: np.ndarray, quality: float) -> np.ndarray:
    """Re-encode as JPEG at the given quality (Pillow defaults: 4:2:0 chroma subsampling)."""
    buf = io.BytesIO()
    Image.fromarray(pixels).save(buf, format="JPEG", quality=int(quality))
    with Image.open(io.BytesIO(buf.getvalue())) as img:
        return np.array(img.convert("RGB"), dtype=np.uint8)


def rescale(pixels: np.ndarray, scale: float) -> np.ndarray:
    """Resize by ``scale`` (bilinear), then back to the original size.

    Restoring the size models a detector that knows the original dimensions; the
    information lost by downsampling remains lost.
    """
    h, w = pixels.shape[:2]
    small = Image.fromarray(pixels).resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.BILINEAR)
    return np.array(small.resize((w, h), Image.BILINEAR), dtype=np.uint8)


def gaussian_noise(pixels: np.ndarray, sigma: float) -> np.ndarray:
    noise = np.random.default_rng(0).normal(0.0, sigma, pixels.shape)
    return np.clip(np.rint(pixels + noise), 0, 255).astype(np.uint8)


def brightness(pixels: np.ndarray, delta: float) -> np.ndarray:
    return np.clip(pixels.astype(np.int16) + int(delta), 0, 255).astype(np.uint8)


def contrast(pixels: np.ndarray, factor: float) -> np.ndarray:
    """Scale deviations from the image mean by ``factor``."""
    mean = pixels.mean()
    return np.clip(np.rint((pixels - mean) * factor + mean), 0, 255).astype(np.uint8)


def crop(pixels: np.ndarray, fraction: float) -> np.ndarray:
    """Discard a border of ``fraction`` of the width/height on every side (filled with black).

    Image dimensions and the position of the remaining content are kept, so this
    measures loss of content, not the geometric desynchronisation of a true crop.
    """
    h, w = pixels.shape[:2]
    dy, dx = int(h * fraction), int(w * fraction)
    out = np.zeros_like(pixels)
    out[dy : h - dy, dx : w - dx] = pixels[dy : h - dy, dx : w - dx]
    return out


@dataclass(frozen=True)
class Attack:
    name: str
    label: str
    parameter_label: str
    presets: tuple[float, ...]
    minimum: float
    maximum: float
    apply: Callable[[np.ndarray, float], np.ndarray]


ATTACKS: dict[str, Attack] = {
    a.name: a
    for a in (
        Attack("jpeg", "JPEG recompression", "quality", (90, 75, 50, 30), 5, 100, jpeg),
        Attack("rescale", "Resize and restore", "scale", (0.75, 0.5), 0.1, 2.0, rescale),
        Attack("noise", "Gaussian noise", "σ", (2, 5, 10), 0, 50, gaussian_noise),
        Attack("brightness", "Brightness shift", "Δ", (20, -20), -128, 128, brightness),
        Attack("contrast", "Contrast scaling", "factor", (0.8, 1.2), 0.1, 3.0, contrast),
        Attack("crop", "Border crop (fill black)", "fraction per side", (0.1, 0.25), 0, 0.45, crop),
    )
}


def apply_attack(pixels: np.ndarray, name: str, parameter: float) -> np.ndarray:
    try:
        attack = ATTACKS[name]
    except KeyError:
        raise ValueError(f"Unknown attack: {name}") from None
    if not attack.minimum <= parameter <= attack.maximum:
        raise ValueError(f"{attack.label} {attack.parameter_label} must be between {attack.minimum} and {attack.maximum}.")
    return attack.apply(pixels, parameter)
