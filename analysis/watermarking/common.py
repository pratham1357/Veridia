"""Types and payload helpers shared by the watermarking schemes (spatial LSB, DCT, DWT)."""

import hashlib
import zlib
from dataclasses import dataclass, field

import numpy as np


class WatermarkError(ValueError):
    """Invalid watermark input or an image the scheme cannot carry/read."""


@dataclass(frozen=True)
class WatermarkVerification:
    status: str  # "verified" | "mismatch" | "extracted" | "not_found"
    message: str | None
    bit_agreement: float | None  # fraction of carriers agreeing with the decoded bits
    parameters: dict[str, int | float | str] = field(default_factory=dict)


def keyed_permutation(total: int, key: str, domain: bytes) -> np.ndarray:
    """Deterministic pseudo-random permutation of ``range(total)`` derived from ``key``."""
    seed = int.from_bytes(hashlib.sha256(domain + key.encode("utf-8")).digest()[:8], "big")
    return np.random.default_rng(seed).permutation(total)


def status_for(text: str, expected: str | None) -> str:
    if expected is None:
        return "extracted"
    return "verified" if text == expected else "mismatch"


def payload_bits(message: bytes, max_bytes: int) -> np.ndarray:
    """Transform-domain payload as a bit array: ``length (1) | message padded | CRC-32 (4)``.

    The same layout the DCT scheme uses, so both carry an identical block format.
    """
    body = bytes([len(message)]) + message.ljust(max_bytes, b"\x00")
    return np.unpackbits(np.frombuffer(body + zlib.crc32(body).to_bytes(4, "big"), dtype=np.uint8))


def parse_payload(bits: np.ndarray, max_bytes: int) -> bytes | None:
    """Inverse of :func:`payload_bits`; ``None`` if the CRC or declared length is invalid."""
    raw = np.packbits(bits).tobytes()
    body, crc = raw[:-4], raw[-4:]
    if zlib.crc32(body).to_bytes(4, "big") != crc or not 1 <= body[0] <= max_bytes:
        return None
    return body[1 : 1 + body[0]]
