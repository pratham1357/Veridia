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

MIN_CROP_PIXELS = 8  # below this a "crop" is a few samples stretched over the canvas, not an experiment


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
    """Add ``delta`` to every sample (clipped to 0..255).

    The parity of ``delta`` matters for least-significant-bit marks. An *even* shift
    leaves every LSB unchanged (except where clipping interferes), so a spatial LSB
    watermark trivially "survives" it, while any *odd* shift flips every LSB and
    destroys it. The presets are therefore odd, so they test the watermark rather
    than the arithmetic. Transform-domain marks are insensitive to the parity.
    """
    return np.clip(pixels.astype(np.int16) + int(delta), 0, 255).astype(np.uint8)


def contrast(pixels: np.ndarray, factor: float) -> np.ndarray:
    """Scale deviations from the image mean by ``factor``."""
    mean = pixels.mean()
    return np.clip(np.rint((pixels - mean) * factor + mean), 0, 255).astype(np.uint8)


def crop(pixels: np.ndarray, fraction: float) -> np.ndarray:
    """Discard a border of ``fraction`` of the width/height on every side (filled with black).

    Image dimensions and the position of the remaining content are kept, so this
    measures loss of content, not the geometric desynchronisation of a true crop.
    Compare with :func:`crop_resync`, which removes the border and shifts what is
    left, so every carrier moves.
    """
    h, w = pixels.shape[:2]
    dy, dx = int(h * fraction), int(w * fraction)
    out = np.zeros_like(pixels)
    out[dy : h - dy, dx : w - dx] = pixels[dy : h - dy, dx : w - dx]
    return out


def crop_resync(pixels: np.ndarray, fraction: float) -> np.ndarray:
    """True crop: cut a border of ``fraction`` per side, then scale back to the original size.

    Unlike :func:`crop`, the surviving content is *moved*: the pixel that was at
    ``(dy, dx)`` ends up at ``(0, 0)`` and is then stretched. Every block and
    wavelet carrier therefore lands on different data, which is what breaks a
    watermark with no geometric resynchronisation. Scaling back to the original
    size keeps the detector's expected geometry, so the failure that remains is
    desynchronisation rather than a shape mismatch.
    """
    h, w = pixels.shape[:2]
    dy, dx = int(h * fraction), int(w * fraction)
    if h - 2 * dy < MIN_CROP_PIXELS or w - 2 * dx < MIN_CROP_PIXELS:
        raise ValueError(
            f"Crop fraction leaves too little of the image: fewer than {MIN_CROP_PIXELS} pixels on a side, "
            "which stretches a handful of samples over the whole canvas rather than testing a watermark."
        )
    kept = Image.fromarray(pixels[dy : h - dy, dx : w - dx])
    return np.array(kept.resize((w, h), Image.BILINEAR), dtype=np.uint8)


def rotate(pixels: np.ndarray, degrees: float) -> np.ndarray:
    """Rotate the content by ``degrees`` about the centre, keeping the canvas size.

    The image stays rotated: this is a genuine geometric attack, not a rotate-and-
    undo. Keeping the canvas size means the detector still sees the dimensions it
    expects, so what defeats it is desynchronisation rather than a shape mismatch.
    Every sample moves to a new row and column, so block-DCT and wavelet carriers
    land on different data, and corners rotated out of frame are filled with black.
    Schemes without geometric resynchronisation are expected to fail here, even at
    a fraction of a degree.
    """
    turned = Image.fromarray(pixels).rotate(degrees, resample=Image.BILINEAR, expand=False)
    return np.array(turned, dtype=np.uint8)


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
        Attack("brightness", "Brightness shift", "Δ", (25, -25), -128, 128, brightness),  # odd on purpose, see brightness()
        Attack("contrast", "Contrast scaling", "factor", (0.8, 1.2), 0.1, 3.0, contrast),
        Attack("crop", "Border crop (fill black)", "fraction per side", (0.1, 0.25), 0, 0.45, crop),
        Attack("crop_resync", "Crop and rescale (shifts content)", "fraction per side", (0.05, 0.1), 0, 0.4, crop_resync),
        Attack("rotate", "Rotation (content stays rotated)", "degrees", (0.5, 2, 5), -45, 45, rotate),
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
