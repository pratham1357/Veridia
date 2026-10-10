"""Blind DWT-domain watermark (detail sub-band coefficient pairs, one-level Haar).

Goal: the same as the spatial and DCT schemes (associate a short verifiable
message with an image), but embedded in wavelet coefficients. Where the DCT
scheme works on independent 8x8 blocks, the wavelet transform is applied to the
whole luminance channel at once, so the carriers are spread across the image
rather than tied to a block grid.

Algorithm
---------
1. Convert RGB to YCbCr (BT.601) and take the luminance channel Y. Chrominance is
   left untouched.
2. Apply a one-level 2-D Haar transform to Y, giving four half-size sub-bands
   ``LL, LH, HL, HH`` (see :mod:`analysis.watermarking.haar`).
3. Each position ``(i, j)`` of the detail bands carries one bit, encoded in the
   relation between the two *directional* detail coefficients at that position:

       bit 1  ->  HL[i, j] - LH[i, j] >= +strength
       bit 0  ->  HL[i, j] - LH[i, j] <= -strength

   If the relation does not already hold, both coefficients move by half the
   shortfall in opposite directions, exactly as the DCT scheme adjusts its pair.

   Why this pair:
   - ``LL`` holds most of the image energy and nearly all of its visible
     structure, so modifying it is the most perceptible option.
   - ``HH`` is diagonal detail and noise, which is what JPEG quantisation and
     blurring discard first, so a mark there is the least durable.
   - ``LH`` and ``HL`` are the horizontal- and vertical-edge bands at the same
     scale. They receive comparable treatment from compression and filtering, so
     their *difference* survives better than either coefficient on its own. This
     is the same reasoning behind the DCT scheme's same-quantisation-step pair.
4. The payload ``length (1) | message padded to 16 bytes | CRC-32 (4)`` (168 bits,
   shared with the DCT scheme via :func:`analysis.watermarking.common.payload_bits`)
   is repeated cyclically over all carrier positions. Bit ``k`` goes to position
   ``perm[k]``, where ``perm`` is a key-derived permutation.
5. Inverse Haar transform, recombine with the untouched chroma, convert to RGB
   and round to 8-bit.

Extraction is *blind* (the original is not needed): recompute the sub-bands, read
``d = HL - LH`` at every carrier, clip each ``d`` to +/- the median ``|d|`` and sum
over all carriers holding the same payload bit, then take the sign and check the
CRC. The clipping stops a few strong edges from outvoting the rest, matching the
DCT decoder.

Measured trade-off
------------------
Because a *one-level* Haar puts ``LH`` and ``HL`` in the highest frequency octave,
this mark is weaker against JPEG than the block-DCT scheme, which uses genuinely
mid-frequency coefficients. At the default strength it survives JPEG down to
quality 61-69 on the project's synthetic test images (30 image/message/chroma-
subsampling configurations, step-1 quality search), where the DCT mark reaches
quality 40-42. Both ranges were measured with Pillow 12.3.0 only.

The alternative of quantising the ``LL`` approximation band (quantisation index
modulation) was implemented and measured during development: it survived JPEG 50
and heavier resizing at comparable PSNR, but **failed brightness and contrast
attacks**, because adding or scaling luminance moves every coefficient off the
quantisation lattice. The sub-band difference used here is invariant to a constant
brightness shift by construction (a DC offset does not reach the detail bands at
all) and tolerates contrast scaling, which scales both coefficients together and
preserves the sign. That invariance, and consistency with the DCT scheme's
mechanism, is why the coefficient pair was kept.

Limitations
-----------
- No geometric resynchronisation: rotation or a true crop shifts every coefficient
  and extraction fails. Resizing only works if the image is restored to its
  original dimensions.
- Weaker than the DCT mark against heavy JPEG recompression (see above).
- Capacity is 16 message bytes, and at least 3 full copies are required
  (504 carriers, i.e. about 48x48 px). An odd final row/column is left untouched.
- Rounding back to 8-bit RGB perturbs the coefficients; redundancy compensates.
- The key selects carrier positions; it is not a cryptographic authentication.
"""

import numpy as np

from analysis.watermarking.common import (
    WatermarkError,
    WatermarkVerification,
    keyed_permutation,
    parse_payload,
    payload_bits,
    status_for,
)
from analysis.watermarking.dct import rgb_to_ycbcr, ycbcr_to_rgb
from analysis.watermarking.haar import haar2, ihaar2

MAX_MESSAGE_BYTES = 16
PAYLOAD_BITS = (1 + MAX_MESSAGE_BYTES + 4) * 8
MIN_COPIES = 3
DEFAULT_STRENGTH = 8.0  # measured: PSNR ~38 dB, SSIM ~0.9, verifies from JPEG quality ~61-69 up on the test images
_DOMAIN = b"veridia-dwt-v1:"


def _grid(pixels: np.ndarray) -> tuple[np.ndarray, int, int]:
    """Luminance-chroma image plus the usable (even) height and width."""
    h, w = (pixels.shape[0] // 2) * 2, (pixels.shape[1] // 2) * 2
    return rgb_to_ycbcr(pixels), h, w


def capacity_carriers(pixels: np.ndarray) -> int:
    """Number of coefficient positions available, one bit each."""
    return (pixels.shape[0] // 2) * (pixels.shape[1] // 2)


def parameters(pixels: np.ndarray, strength: float | None = None) -> dict[str, int | float | str]:
    carriers = capacity_carriers(pixels)
    params: dict[str, int | float | str] = {
        "domain": "one-level 2-D Haar DWT of luminance (Y)",
        "coefficients": "HL vs LH detail sub-bands",
        "carriers": carriers,
        "payload_bits": PAYLOAD_BITS,
        "copies": round(carriers / PAYLOAD_BITS, 2),
    }
    if strength is not None:
        params["strength"] = strength
    return params


def _differences(pixels: np.ndarray, key: str) -> np.ndarray:
    """``HL - LH`` at every carrier, in permuted (payload stream) order."""
    ycc, h, w = _grid(pixels)
    _, lh, hl, _ = haar2(ycc[:h, :w, 0] - 128.0)
    d = (hl - lh).reshape(-1)
    return d[keyed_permutation(d.size, key, _DOMAIN)]


def embed(pixels: np.ndarray, message: str, key: str = "", strength: float = DEFAULT_STRENGTH) -> np.ndarray:
    """Return a watermarked copy of ``pixels``. The input is not modified."""
    data = message.encode("utf-8")
    if not 1 <= len(data) <= MAX_MESSAGE_BYTES:
        raise WatermarkError(f"DWT watermark message must be 1-{MAX_MESSAGE_BYTES} bytes (UTF-8).")
    if not 1 <= strength <= 200:
        raise WatermarkError("Strength must be between 1 and 200.")
    carriers = capacity_carriers(pixels)
    if carriers < PAYLOAD_BITS * MIN_COPIES:
        raise WatermarkError(
            f"Image is too small for the DWT watermark: needs at least {PAYLOAD_BITS * MIN_COPIES} carriers "
            f"(has {carriers})."
        )

    ycc, h, w = _grid(pixels)
    ll, lh, hl, hh = haar2(ycc[:h, :w, 0] - 128.0)
    shape = lh.shape
    lh_flat, hl_flat = lh.reshape(-1), hl.reshape(-1)

    order = keyed_permutation(lh_flat.size, key, _DOMAIN)
    sign = np.resize(payload_bits(data, MAX_MESSAGE_BYTES), order.size).astype(np.float64) * 2 - 1  # 1 -> +1, 0 -> -1

    a, b = hl_flat[order], lh_flat[order]
    shortfall = np.maximum(0.0, strength - sign * (a - b))  # how far the pair is from the required side
    hl_flat[order] = a + sign * shortfall / 2
    lh_flat[order] = b - sign * shortfall / 2

    ycc[:h, :w, 0] = ihaar2(ll, lh_flat.reshape(shape), hl_flat.reshape(shape), hh) + 128.0
    marked = ycbcr_to_rgb(ycc)
    return marked if (h, w) == pixels.shape[:2] else _merge(pixels, marked, h, w)


def _merge(original: np.ndarray, marked: np.ndarray, h: int, w: int) -> np.ndarray:
    """Keep an odd final row/column byte-identical to the original."""
    out = original.copy()
    out[:h, :w] = marked[:h, :w]
    return out


def verify(pixels: np.ndarray, key: str = "", expected: str | None = None) -> WatermarkVerification:
    params = parameters(pixels)
    if capacity_carriers(pixels) // PAYLOAD_BITS < MIN_COPIES:
        return WatermarkVerification("not_found", None, None, params)
    d = _differences(pixels, key)
    idx = np.arange(d.size) % PAYLOAD_BITS
    limit = float(np.median(np.abs(d))) or 1.0
    score = np.bincount(idx, weights=np.clip(d, -limit, limit), minlength=PAYLOAD_BITS)
    bits = (score > 0).astype(np.uint8)
    message = parse_payload(bits, MAX_MESSAGE_BYTES)
    if message is None:
        return WatermarkVerification("not_found", None, None, params)
    try:
        text = message.decode("utf-8")
    except UnicodeDecodeError:
        return WatermarkVerification("not_found", None, None, params)
    agreement = float(np.mean((d > 0) == bits[idx].astype(bool)))
    return WatermarkVerification(status_for(text, expected), text, agreement, params)


def bit_error_rate(pixels: np.ndarray, message: str, key: str = "") -> float | None:
    """Fraction of carriers whose individual bit differs from what was embedded (before voting)."""
    if capacity_carriers(pixels) < PAYLOAD_BITS:
        return None
    d = _differences(pixels, key)
    expected = np.resize(payload_bits(message.encode("utf-8"), MAX_MESSAGE_BYTES), d.size).astype(bool)
    return float(np.mean((d > 0) != expected))
