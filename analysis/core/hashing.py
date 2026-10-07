import hashlib


def sha256_hex(data: bytes) -> str:
    """SHA-256 of raw bytes, as lowercase hex."""
    return hashlib.sha256(data).hexdigest()
