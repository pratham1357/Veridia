"""Types shared by the watermarking schemes (spatial LSB and DCT)."""

import hashlib
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
