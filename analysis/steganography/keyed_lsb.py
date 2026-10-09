"""Keyed LSB steganography using deterministic pseudo-random sample ordering.

The same key and image shape reproduce the same sample ordering, allowing
payload extraction. SHA-256 is used to derive a NumPy PRNG seed for this
demonstration; this is NOT production-grade cryptography.

The embedded stream is:
    magic (4 bytes) | payload length (4 bytes, big-endian) | payload

The image must be stored losslessly, such as PNG. This method does not
encrypt the payload and does not guarantee resistance to steganalysis.
"""

import hashlib

import numpy as np

MAGIC = b"VKLS"
HEADER_BYTES = 8


class KeyedLsbError(ValueError):
    """Base error for keyed LSB operations."""


class CapacityError(KeyedLsbError):
    """Payload exceeds the available image capacity."""


class NoPayloadError(KeyedLsbError):
    """No valid keyed LSB payload was found."""


def _validate_pixels(pixels: np.ndarray) -> None:
    if not isinstance(pixels, np.ndarray):
        raise KeyedLsbError("Pixels must be a NumPy array.")
    if pixels.dtype != np.uint8:
        raise KeyedLsbError("Pixels must have dtype uint8.")
    if pixels.size == 0 or pixels.ndim not in (2, 3):
        raise KeyedLsbError("Pixels must be a non-empty grayscale or color image.")
    if pixels.ndim == 3 and pixels.shape[2] not in (1, 3, 4):
        raise KeyedLsbError("Color images must have 1, 3, or 4 channels.")


def _ordering(pixels: np.ndarray, key: str | bytes) -> np.ndarray:
    """Create a reproducible pseudo-random ordering for this key and image."""
    if isinstance(key, str):
        key_bytes = key.encode("utf-8")
    elif isinstance(key, bytes):
        key_bytes = key
    else:
        raise KeyedLsbError("Key must be a string or bytes.")

    if not key_bytes:
        raise KeyedLsbError("Key must not be empty.")

    material = (
        b"VERIDIA-DEMO-KEYED-LSB-v1"
        + len(key_bytes).to_bytes(4, "big")
        + key_bytes
        + repr(pixels.shape).encode("ascii")
    )
    seed = int.from_bytes(hashlib.sha256(material).digest()[:16], "big")
    return np.random.default_rng(seed).permutation(pixels.size)


def capacity_bytes(pixels: np.ndarray) -> int:
    """Maximum payload bytes, excluding the eight-byte header."""
    _validate_pixels(pixels)
    return max(0, pixels.size // 8 - HEADER_BYTES)


def embed(pixels: np.ndarray, payload: bytes, key: str | bytes) -> np.ndarray:
    """Embed bytes using keyed pseudo-random ordering; never modify the input."""
    _validate_pixels(pixels)

    if not isinstance(payload, bytes) or not payload:
        raise KeyedLsbError("Payload must be non-empty bytes.")

    capacity = capacity_bytes(pixels)
    if len(payload) > capacity:
        raise CapacityError(
            f"Payload is {len(payload)} bytes; maximum capacity is {capacity} bytes."
        )

    stream = MAGIC + len(payload).to_bytes(4, "big") + payload
    bits = np.unpackbits(np.frombuffer(stream, dtype=np.uint8))

    result = pixels.copy()
    flat = result.reshape(-1)
    order = _ordering(pixels, key)
    positions = order[:bits.size]
    flat[positions] = (flat[positions] & 0xFE) | bits

    return result


def extract(pixels: np.ndarray, key: str | bytes) -> bytes:
    """Extract a payload using the same key used for embedding."""
    _validate_pixels(pixels)

    if pixels.size < HEADER_BYTES * 8:
        raise NoPayloadError("Image is too small to contain a payload header.")

    order = _ordering(pixels, key)
    flat = pixels.reshape(-1)

    header_positions = order[: HEADER_BYTES * 8]
    header = np.packbits(flat[header_positions] & 1).tobytes()

    if header[:4] != MAGIC:
        raise NoPayloadError("No keyed LSB payload found; check the key or image.")

    length = int.from_bytes(header[4:8], "big")
    if length == 0 or length > capacity_bytes(pixels):
        raise NoPayloadError("Invalid payload length in header.")

    bit_count = (HEADER_BYTES + length) * 8
    positions = order[:bit_count]
    stream = np.packbits(flat[positions] & 1).tobytes()

    return stream[HEADER_BYTES:]


def embed_text(pixels: np.ndarray, text: str, key: str | bytes) -> np.ndarray:
    """Embed UTF-8 text."""
    if not isinstance(text, str) or not text:
        raise KeyedLsbError("Text must not be empty.")
    return embed(pixels, text.encode("utf-8"), key)


def extract_text(pixels: np.ndarray, key: str | bytes) -> str:
    """Extract UTF-8 text."""
    try:
        return extract(pixels, key).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise NoPayloadError("Extracted payload is not valid UTF-8 text.") from exc
