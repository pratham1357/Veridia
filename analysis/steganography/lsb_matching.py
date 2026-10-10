"""LSB Matching (±1) steganography.

Embeds each payload bit by checking the sample's least significant bit.
If it differs, the sample is adjusted by +1 or -1, chosen pseudo-randomly.
Pixel values remain within [0, 255].

This is a demonstration implementation, not a cryptographic system.
"""

import numpy as np


class LsbMatchingError(ValueError):
    """Invalid input or insufficient image capacity."""


def _validate_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise LsbMatchingError("Image must be a NumPy array.")
    if image.dtype != np.uint8:
        raise LsbMatchingError("Image must have dtype uint8.")
    if image.ndim not in (2, 3) or image.size == 0:
        raise LsbMatchingError("Image must be a non-empty grayscale or color array.")
    if image.ndim == 3 and image.shape[2] not in (1, 3, 4):
        raise LsbMatchingError("Image must have 1, 3, or 4 channels.")


def embed(image: np.ndarray, payload: bytes, seed: int = 0) -> np.ndarray:
    """Embed bytes using ±1 matching and deterministic sample ordering."""
    _validate_image(image)

    if not isinstance(payload, bytes) or not payload:
        raise LsbMatchingError("Payload must be non-empty bytes.")

    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
    if bits.size > image.size:
        raise LsbMatchingError("Payload exceeds image capacity.")

    rng = np.random.default_rng(seed)
    order = rng.permutation(image.size)[:bits.size]

    result = image.copy()
    flat = result.reshape(-1)

    # Vectorised: work on all selected samples at once instead of one bit at a time.
    # The sample order is drawn first, exactly as in extract(), so extraction is unchanged.
    values = flat[order].astype(np.int16)  # signed arithmetic; the guards below keep the result in 0..255
    mismatch = (values & 1) != bits
    steps = rng.choice(np.array([-1, 1], dtype=np.int16), size=values.size)
    steps[values == 0] = 1  # 0 can only go up, never wrap to 255
    steps[values == 255] = -1  # 255 can only go down, never wrap to 0
    flat[order] = np.where(mismatch, values + steps, values).astype(np.uint8)

    return result


def extract(image: np.ndarray, payload_length: int, seed: int = 0) -> bytes:
    """Extract a known-length payload using the same deterministic ordering."""
    _validate_image(image)

    if not isinstance(payload_length, int) or isinstance(payload_length, bool):
        raise LsbMatchingError("Payload length must be an integer.")
    if payload_length <= 0:
        raise LsbMatchingError("Payload length must be positive.")

    bit_count = payload_length * 8
    if bit_count > image.size:
        raise LsbMatchingError("Payload length exceeds image capacity.")

    rng = np.random.default_rng(seed)
    order = rng.permutation(image.size)[:bit_count]
    bits = image.reshape(-1)[order] & 1

    return np.packbits(bits).tobytes()
