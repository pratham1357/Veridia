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

    for position, bit in zip(order, bits):
        value = int(flat[position])
        if (value & 1) != int(bit):
            if value == 0:
                flat[position] = 1
            elif value == 255:
                flat[position] = 254
            else:
                flat[position] = value + int(rng.choice([-1, 1]))

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
