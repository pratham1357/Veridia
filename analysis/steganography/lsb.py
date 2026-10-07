"""LSB steganography in the spatial domain.

Goal: conceal a message inside a cover image (information hiding).

Algorithm
---------
The cover is an 8-bit RGB array. Its samples are read in row-major order, R then G
then B for each pixel, and the least significant bit of each sample carries one
payload bit (MSB-first within each byte), starting at the first sample.

Embedded stream (big-endian)::

    magic "VRDS" (4 bytes) | payload length (4 bytes) | payload bytes

Capacity is ``H * W * 3 // 8 - 8`` payload bytes. Nothing is encrypted or
scrambled: anyone who knows the format can read the payload, and the sequential
layout is easy to detect statistically. This is a baseline for teaching and
later steganalysis work, not a secure channel.
"""

import numpy as np

MAGIC = b"VRDS"
HEADER_BYTES = 8


class LsbError(ValueError):
    """Base class for LSB embedding/extraction failures."""


class CapacityError(LsbError):
    """The payload does not fit in the cover image."""


class NoPayloadError(LsbError):
    """No valid VERIDIA LSB payload was found."""


def capacity_bytes(pixels: np.ndarray) -> int:
    """Maximum payload size in bytes (excluding the 8-byte header)."""
    return max(0, pixels.size // 8 - HEADER_BYTES)


def capacity_report(pixels: np.ndarray, payload_bytes: int) -> dict[str, float | int]:
    cap = capacity_bytes(pixels)
    return {
        "capacity_bytes": cap,
        "payload_bytes": payload_bytes,
        "utilization_percent": round(100.0 * payload_bytes / cap, 4) if cap else 0.0,
    }


def embed(pixels: np.ndarray, payload: bytes) -> np.ndarray:
    """Return a copy of ``pixels`` with ``payload`` embedded. The input is not modified."""
    if not payload:
        raise LsbError("Payload is empty.")
    cap = capacity_bytes(pixels)
    if len(payload) > cap:
        raise CapacityError(f"Payload is {len(payload)} bytes but this image can hold at most {cap} bytes.")
    stream = MAGIC + len(payload).to_bytes(4, "big") + payload
    bits = np.unpackbits(np.frombuffer(stream, dtype=np.uint8))
    flat = pixels.reshape(-1).copy()
    flat[: bits.size] = (flat[: bits.size] & 0xFE) | bits
    return flat.reshape(pixels.shape)


def extract(pixels: np.ndarray) -> bytes:
    """Recover an embedded payload, or raise ``NoPayloadError``."""
    flat = pixels.reshape(-1)
    header_bits = HEADER_BYTES * 8
    if flat.size < header_bits:
        raise NoPayloadError("Image is too small to contain a payload.")
    header = np.packbits(flat[:header_bits] & 1).tobytes()
    if header[:4] != MAGIC:
        raise NoPayloadError("No VERIDIA LSB payload header found.")
    length = int.from_bytes(header[4:], "big")
    if length == 0 or length > capacity_bytes(pixels):
        raise NoPayloadError("Payload header is present but its length is invalid.")
    return np.packbits(flat[header_bits : header_bits + length * 8] & 1).tobytes()


def embed_text(pixels: np.ndarray, text: str) -> np.ndarray:
    return embed(pixels, text.encode("utf-8"))


def extract_text(pixels: np.ndarray) -> str:
    try:
        return extract(pixels).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise NoPayloadError("A payload header was found but the payload is not valid UTF-8 text.") from exc
