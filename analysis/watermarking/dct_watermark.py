"""Blind DCT-domain watermark (coefficient-pair relationship, after Koch & Zhao).

Goal: the same as the spatial watermark (associate a short verifiable message
with an image) but embedded in transform coefficients, so it can survive
operations that rewrite pixel LSBs, such as JPEG recompression.

Algorithm
---------
1. Convert RGB to YCbCr (BT.601) and take the luminance channel Y. Chrominance is
   left untouched.
2. Split Y into non-overlapping 8x8 blocks (a right/bottom remainder smaller than
   8 px is not used) and apply the 2-D DCT-II to each block.
3. Each block carries one bit, encoded in the relation between two mid-frequency
   coefficients ``C[4,1]`` and ``C[3,2]``:

       bit 1  ->  C[4,1] - C[3,2] >= +strength
       bit 0  ->  C[4,1] - C[3,2] <= -strength

   If the relation does not already hold, both coefficients are moved by half the
   shortfall in opposite directions. These positions are chosen because:
   - low frequencies (near DC) carry most visible structure, so changes there are
     more perceptible;
   - high frequencies are what JPEG quantisation discards first;
   - both positions have the same step (22) in the standard JPEG luminance
     quantisation table, so recompression tends to disturb them similarly and the
     *difference* is preserved better than either value alone.
4. The payload block ``length (1) | message padded to 16 bytes | CRC-32 (4)``
   (168 bits) is repeated cyclically over all 8x8 blocks. Bit ``k`` goes to block
   ``perm[k]``, where ``perm`` is a key-derived permutation of block indices.
5. Inverse DCT, recombine with the original chroma, convert to RGB and round.

Extraction is *blind* (the original is not needed): recompute the block DCTs,
read ``d = C[4,1] - C[3,2]`` for every block, clip each ``d`` to +/- the median
``|d|`` and sum over all blocks carrying the same payload bit (clipped soft-decision
voting), take the sign, and check the CRC. Clipping stops a few blocks with very
large natural coefficients (strong edges) from outvoting the rest; experimentally it
decoded better than both plain soft voting and a hard majority vote.

Limitations
-----------
- No geometric resynchronisation: rotation, true cropping, or any shift of the
  8x8 grid breaks extraction. Resizing only works if the image is restored to its
  original dimensions.
- Rounding to 8-bit RGB and clipping in very dark/bright regions perturb the
  coefficients; redundancy compensates, but tiny images may fail.
- Capacity is low: at most 16 message bytes, and at least 3 full copies are
  required (504 blocks, e.g. about 180x180 px).
- The key selects block positions; it is not a cryptographic authentication.
"""

import zlib

import numpy as np

from analysis.watermarking.common import WatermarkError, WatermarkVerification, keyed_permutation, status_for
from analysis.watermarking.dct import BLOCK, block_dct, block_idct, rgb_to_ycbcr, ycbcr_to_rgb

MAX_MESSAGE_BYTES = 16
PAYLOAD_BITS = (1 + MAX_MESSAGE_BYTES + 4) * 8
MIN_COPIES = 3
COEFF_A = (4, 1)
COEFF_B = (3, 2)
DEFAULT_STRENGTH = 25.0
_DOMAIN = b"veridia-dct-v1:"


def _payload_bits(message: bytes) -> np.ndarray:
    body = bytes([len(message)]) + message.ljust(MAX_MESSAGE_BYTES, b"\x00")
    return np.unpackbits(np.frombuffer(body + zlib.crc32(body).to_bytes(4, "big"), dtype=np.uint8))


def _parse(bits: np.ndarray) -> bytes | None:
    raw = np.packbits(bits).tobytes()
    body, crc = raw[:-4], raw[-4:]
    if zlib.crc32(body).to_bytes(4, "big") != crc or not 1 <= body[0] <= MAX_MESSAGE_BYTES:
        return None
    return body[1 : 1 + body[0]]


def _grid(pixels: np.ndarray) -> tuple[np.ndarray, int, int]:
    """Luminance-chroma image plus the usable (multiple-of-8) height and width."""
    h, w = (pixels.shape[0] // BLOCK) * BLOCK, (pixels.shape[1] // BLOCK) * BLOCK
    return rgb_to_ycbcr(pixels), h, w


def capacity_blocks(pixels: np.ndarray) -> int:
    return (pixels.shape[0] // BLOCK) * (pixels.shape[1] // BLOCK)


def parameters(pixels: np.ndarray, strength: float | None = None) -> dict[str, int | float | str]:
    blocks = capacity_blocks(pixels)
    params: dict[str, int | float | str] = {
        "domain": "8x8 block DCT of luminance (Y)",
        "coefficients": f"C{COEFF_A} vs C{COEFF_B}",
        "blocks": blocks,
        "payload_bits": PAYLOAD_BITS,
        "copies": round(blocks / PAYLOAD_BITS, 2),
    }
    if strength is not None:
        params["strength"] = strength
    return params


def _differences(pixels: np.ndarray, key: str) -> np.ndarray:
    """``C[4,1] - C[3,2]`` per block, in permuted (stream) order."""
    ycc, h, w = _grid(pixels)
    coeffs = block_dct(ycc[:h, :w, 0] - 128.0).reshape(-1, BLOCK, BLOCK)
    d = coeffs[:, COEFF_A[0], COEFF_A[1]] - coeffs[:, COEFF_B[0], COEFF_B[1]]
    return d[keyed_permutation(d.size, key, _DOMAIN)]


def embed(pixels: np.ndarray, message: str, key: str = "", strength: float = DEFAULT_STRENGTH) -> np.ndarray:
    """Return a watermarked copy of ``pixels``. The input is not modified."""
    data = message.encode("utf-8")
    if not 1 <= len(data) <= MAX_MESSAGE_BYTES:
        raise WatermarkError(f"DCT watermark message must be 1-{MAX_MESSAGE_BYTES} bytes (UTF-8).")
    if not 1 <= strength <= 200:
        raise WatermarkError("Strength must be between 1 and 200.")
    if capacity_blocks(pixels) < PAYLOAD_BITS * MIN_COPIES:
        raise WatermarkError(
            f"Image is too small for the DCT watermark: needs at least {PAYLOAD_BITS * MIN_COPIES} 8x8 blocks "
            f"(has {capacity_blocks(pixels)})."
        )

    ycc, h, w = _grid(pixels)
    coeffs = block_dct(ycc[:h, :w, 0] - 128.0)
    flat = coeffs.reshape(-1, BLOCK, BLOCK)  # view onto coeffs
    n = flat.shape[0]
    order = keyed_permutation(n, key, _DOMAIN)
    sign = np.resize(_payload_bits(data), n).astype(np.float64) * 2 - 1  # bit 1 -> +1, bit 0 -> -1

    a = flat[order, COEFF_A[0], COEFF_A[1]]
    b = flat[order, COEFF_B[0], COEFF_B[1]]
    shortfall = np.maximum(0.0, strength - sign * (a - b))  # how far d is from the required side
    flat[order, COEFF_A[0], COEFF_A[1]] = a + sign * shortfall / 2
    flat[order, COEFF_B[0], COEFF_B[1]] = b - sign * shortfall / 2

    ycc[:h, :w, 0] = block_idct(coeffs) + 128.0
    return ycbcr_to_rgb(ycc) if (h, w) == pixels.shape[:2] else _merge(pixels, ycbcr_to_rgb(ycc), h, w)


def _merge(original: np.ndarray, marked: np.ndarray, h: int, w: int) -> np.ndarray:
    """Keep the unused right/bottom remainder byte-identical to the original."""
    out = original.copy()
    out[:h, :w] = marked[:h, :w]
    return out


def verify(pixels: np.ndarray, key: str = "", expected: str | None = None) -> WatermarkVerification:
    params = parameters(pixels)
    copies = capacity_blocks(pixels) // PAYLOAD_BITS
    if copies < MIN_COPIES:
        return WatermarkVerification("not_found", None, None, params)
    d = _differences(pixels, key)
    idx = np.arange(d.size) % PAYLOAD_BITS
    limit = float(np.median(np.abs(d))) or 1.0
    score = np.bincount(idx, weights=np.clip(d, -limit, limit), minlength=PAYLOAD_BITS)
    bits = (score > 0).astype(np.uint8)
    message = _parse(bits)
    if message is None:
        return WatermarkVerification("not_found", None, None, params)
    try:
        text = message.decode("utf-8")
    except UnicodeDecodeError:
        return WatermarkVerification("not_found", None, None, params)
    agreement = float(np.mean((d > 0) == bits[idx].astype(bool)))
    return WatermarkVerification(status_for(text, expected), text, agreement, params)


def bit_error_rate(pixels: np.ndarray, message: str, key: str = "") -> float | None:
    """Fraction of blocks whose individual bit differs from what was embedded (before voting)."""
    if capacity_blocks(pixels) < PAYLOAD_BITS:
        return None
    d = _differences(pixels, key)
    expected = np.resize(_payload_bits(message.encode("utf-8")), d.size).astype(bool)
    return float(np.mean((d > 0) != expected))
