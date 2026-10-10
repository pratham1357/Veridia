"""One-level 2-D Haar wavelet transform (implemented directly with NumPy, no wavelet library).

The Haar transform is the simplest wavelet: it repeatedly replaces each adjacent
pair of samples ``(x0, x1)`` with their normalised sum and difference::

    approximation = (x0 + x1) / sqrt(2)
    detail        = (x0 - x1) / sqrt(2)

The ``1/sqrt(2)`` factors make the transform *orthonormal*, so it preserves total
energy and its inverse is just the same butterfly run backwards. Applying it
along the width and then along the height splits a channel into four sub-bands,
each half the height and half the width of the input:

===== ==================================================================
LL    both directions low-pass: a half-size blurred copy of the image
LH    low-pass horizontally, high-pass vertically: horizontal edges
HL    high-pass horizontally, low-pass vertically: vertical edges
HH    high-pass both ways: diagonal detail and noise
===== ==================================================================

Reconstruction is exact to floating-point rounding (see ``tests/test_dwt_watermark.py``).

The input height and width must be even. Callers crop to an even size and leave
any odd final row/column untouched, as the block-DCT code does with its 8x8 grid.
"""

import numpy as np

SQRT2 = np.sqrt(2.0)


def haar2(channel: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Forward one-level 2-D Haar transform of a float channel with even dimensions.

    Returns ``(LL, LH, HL, HH)``, each of shape ``(H / 2, W / 2)``.
    """
    if channel.ndim != 2:
        raise ValueError("Haar transform expects a 2-D channel.")
    if channel.shape[0] % 2 or channel.shape[1] % 2:
        raise ValueError(f"Haar transform needs even dimensions, got {channel.shape}.")

    # Along the width: pair up columns.
    low = (channel[:, 0::2] + channel[:, 1::2]) / SQRT2
    high = (channel[:, 0::2] - channel[:, 1::2]) / SQRT2
    # Along the height: pair up rows of each half.
    ll = (low[0::2] + low[1::2]) / SQRT2
    lh = (low[0::2] - low[1::2]) / SQRT2
    hl = (high[0::2] + high[1::2]) / SQRT2
    hh = (high[0::2] - high[1::2]) / SQRT2
    return ll, lh, hl, hh


def ihaar2(ll: np.ndarray, lh: np.ndarray, hl: np.ndarray, hh: np.ndarray) -> np.ndarray:
    """Inverse of :func:`haar2`. Returns a channel of shape ``(2 * h, 2 * w)``."""
    shapes = {a.shape for a in (ll, lh, hl, hh)}
    if len(shapes) != 1:
        raise ValueError(f"Sub-bands must share one shape, got {sorted(shapes)}.")
    h, w = ll.shape

    # Undo the height pass.
    low = np.empty((2 * h, w), dtype=np.float64)
    high = np.empty((2 * h, w), dtype=np.float64)
    low[0::2], low[1::2] = (ll + lh) / SQRT2, (ll - lh) / SQRT2
    high[0::2], high[1::2] = (hl + hh) / SQRT2, (hl - hh) / SQRT2
    # Undo the width pass.
    channel = np.empty((2 * h, 2 * w), dtype=np.float64)
    channel[:, 0::2], channel[:, 1::2] = (low + high) / SQRT2, (low - high) / SQRT2
    return channel


def subband_preview(pixels: np.ndarray) -> np.ndarray:
    """Visualisation: the four sub-bands tiled as LL/LH over HL/HH, scaled to 0-255.

    LL is shown on its own scale (it holds most of the energy); the three detail
    bands share a scale so their relative magnitudes stay comparable.
    """
    from analysis.watermarking.dct import rgb_to_ycbcr

    y = rgb_to_ycbcr(pixels)[..., 0]
    h, w = (y.shape[0] // 2) * 2, (y.shape[1] // 2) * 2
    ll, lh, hl, hh = haar2(y[:h, :w])

    def norm(band: np.ndarray, gain: float = 1.0) -> np.ndarray:
        peak = float(np.abs(band).max()) or 1.0
        return np.clip(np.abs(band) * gain * 255.0 / peak, 0, 255).astype(np.uint8)

    detail_peak = max(float(np.abs(b).max()) for b in (lh, hl, hh)) or 1.0
    scaled = [np.clip(np.abs(b) * 255.0 / detail_peak, 0, 255).astype(np.uint8) for b in (lh, hl, hh)]
    return np.block([[norm(ll), scaled[0]], [scaled[1], scaled[2]]])
