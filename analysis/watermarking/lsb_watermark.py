"""Keyed, redundant spatial-domain (LSB) watermark.

Goal: associate a short identifying message (e.g. an owner tag) with an image so it
can later be verified. Contrast with steganography, whose goal is concealing a
message to be communicated.

Algorithm
---------
1. Build a fixed-size block (73 bytes = 584 bits)::

       magic "VRDW" (4) | message length (1) | message padded with zeros to 64 | CRC-32 (4)

   The CRC covers the length byte and the padded message.
2. Derive a pseudo-random permutation of all colour-sample positions from the key
   (SHA-256 of the key seeds NumPy's PCG64 generator). The same key gives the same
   positions, so embedding is deterministic.
3. Repeat the block cyclically over all samples and write bit ``k`` of the repeated
   stream into the LSB of sample ``perm[k]``. The block is therefore spread across
   the whole image, with at least 3 full copies.
4. Verification re-derives the permutation, reads the LSBs, takes a per-bit majority
   vote across the copies, and checks the magic value and CRC.

Properties and limitations
--------------------------
- Invisible in normal viewing (each sample changes by at most 1).
- Majority voting tolerates a small amount of random bit damage, but this is a
  *fragile* watermark: JPEG compression, resizing, cropping, or filtering will
  destroy it. It is not robust against attacks.
- With an empty key the permutation is derivable by anyone, so the watermark is
  not secret and is not a security guarantee. A secret key only makes locating
  the bits harder; it does not authenticate the image.
- Embedding overwrites the LSBs of every sample, so any LSB steganography payload in
  the same image is destroyed.
"""

import hashlib
import zlib
from dataclasses import dataclass

import numpy as np

MAGIC = b"VRDW"
MAX_MESSAGE_BYTES = 64
BLOCK_BYTES = 4 + 1 + MAX_MESSAGE_BYTES + 4
BLOCK_BITS = BLOCK_BYTES * 8
MIN_COPIES = 3


class WatermarkError(ValueError):
    """Invalid watermark input or image."""


@dataclass(frozen=True)
class WatermarkVerification:
    status: str  # "verified" | "mismatch" | "extracted" | "not_found"
    message: str | None
    bit_agreement: float | None  # fraction of LSBs agreeing with the voted block


def _positions(total: int, key: str) -> np.ndarray:
    seed = int.from_bytes(hashlib.sha256(b"veridia-wm-v1:" + key.encode("utf-8")).digest()[:8], "big")
    return np.random.default_rng(seed).permutation(total)


def _build_block(message: bytes) -> bytes:
    body = bytes([len(message)]) + message.ljust(MAX_MESSAGE_BYTES, b"\x00")
    return MAGIC + body + zlib.crc32(body).to_bytes(4, "big")


def _parse_block(block: bytes) -> bytes | None:
    if block[:4] != MAGIC:
        return None
    body, crc = block[4:-4], block[-4:]
    if zlib.crc32(body).to_bytes(4, "big") != crc or not 1 <= body[0] <= MAX_MESSAGE_BYTES:
        return None
    return body[1 : 1 + body[0]]


def embed(pixels: np.ndarray, message: str, key: str = "") -> np.ndarray:
    """Return a copy of ``pixels`` carrying the watermark. The input is not modified."""
    data = message.encode("utf-8")
    if not 1 <= len(data) <= MAX_MESSAGE_BYTES:
        raise WatermarkError(f"Watermark message must be 1-{MAX_MESSAGE_BYTES} bytes (UTF-8).")
    total = pixels.size
    if total < BLOCK_BITS * MIN_COPIES:
        raise WatermarkError("Image is too small to carry the watermark with sufficient redundancy.")
    bits = np.resize(np.unpackbits(np.frombuffer(_build_block(data), dtype=np.uint8)), total)
    perm = _positions(total, key)
    flat = pixels.reshape(-1).copy()
    flat[perm] = (flat[perm] & 0xFE) | bits
    return flat.reshape(pixels.shape)


def verify(pixels: np.ndarray, key: str = "", expected: str | None = None) -> WatermarkVerification:
    """Extract the watermark and, if ``expected`` is given, compare against it."""
    total = pixels.size
    copies = total // BLOCK_BITS
    if copies < MIN_COPIES:
        return WatermarkVerification("not_found", None, None)
    lsbs = (pixels.reshape(-1)[_positions(total, key)] & 1)[: copies * BLOCK_BITS].reshape(copies, BLOCK_BITS)
    voted = (lsbs.sum(axis=0, dtype=np.int64) * 2 > copies).astype(np.uint8)
    message = _parse_block(np.packbits(voted).tobytes())
    if message is None:
        return WatermarkVerification("not_found", None, None)
    agreement = float(np.mean(lsbs == voted))
    try:
        text = message.decode("utf-8")
    except UnicodeDecodeError:
        return WatermarkVerification("not_found", None, None)
    if expected is None:
        status = "extracted"
    else:
        status = "verified" if text == expected else "mismatch"
    return WatermarkVerification(status, text, agreement)
