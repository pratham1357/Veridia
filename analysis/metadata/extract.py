"""Image metadata extraction.

Every field is reported with an explicit status so that absent data is never
confused with unknown data:

- ``available``     the value was present and read
- ``not_available`` the image does not carry this information
- ``unknown``       the information may exist but could not be interpreted
"""

import io
from typing import Any

from PIL import ExifTags, Image

# Bits per channel for Pillow modes, as decoded.
_BITS_PER_CHANNEL = {"1": 1, "L": 8, "P": 8, "RGB": 8, "RGBA": 8, "LA": 8, "CMYK": 8, "I;16": 16, "I": 32, "F": 32}

# EXIF pointer tags that only point at sub-IFDs (which are read separately).
_POINTER_TAGS = {0x8769, 0x8825, 0xA005}

_MAX_TEXT = 256


def _field(value: Any, *, missing: bool = False) -> dict[str, Any]:
    if missing:
        return {"status": "not_available", "value": None}
    if value is None:
        return {"status": "unknown", "value": None}
    return {"status": "available", "value": value}


def _safe(value: Any) -> Any:
    """Convert an EXIF value to something JSON-serializable without inventing data."""
    if isinstance(value, bytes):
        text = value.rstrip(b"\x00")
        if text and all(32 <= b < 127 for b in text) and len(text) <= _MAX_TEXT:
            return text.decode("ascii")
        return f"<{len(value)} bytes>"
    if isinstance(value, str):
        return value.replace("\x00", "")[:_MAX_TEXT]
    if isinstance(value, (bool, int)):
        return value
    if isinstance(value, (tuple, list)):
        return [_safe(v) for v in value]
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        try:
            return float(value)
        except (ZeroDivisionError, ValueError):
            return str(value)
    if isinstance(value, float):
        return value if value == value else None  # NaN is not valid JSON
    return str(value)[:_MAX_TEXT]


def _exif_entries(exif: Image.Exif) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for tag, value in exif.items():
        if tag in _POINTER_TAGS:
            continue
        entries.append({"ifd": "IFD0", "tag": ExifTags.TAGS.get(tag, f"0x{tag:04X}"), "value": _safe(value)})
    for ifd, name, names in ((ExifTags.IFD.Exif, "Exif", ExifTags.TAGS), (ExifTags.IFD.GPSInfo, "GPS", ExifTags.GPSTAGS)):
        try:
            sub = exif.get_ifd(ifd)
        except Exception:
            continue
        for tag, value in sub.items():
            entries.append({"ifd": name, "tag": names.get(tag, f"0x{tag:04X}"), "value": _safe(value)})
    return entries


def extract_metadata(data: bytes) -> dict[str, Any]:
    """Extract basic metadata and EXIF from image bytes. Does not modify the input."""
    with Image.open(io.BytesIO(data)) as img:
        try:
            raw_exif = img.getexif()

            # Force Pillow to load the nested EXIF IFD, including DateTimeOriginal.
            try:
                raw_exif.get_ifd(ExifTags.IFD.Exif)
            except Exception:
                pass

            entries = _exif_entries(raw_exif)
            exif = {"status": "available" if entries else "not_available", "entries": entries}
        except Exception:
            exif = {"status": "unknown", "entries": []}

        return {
            "format": _field(img.format),
            "width": _field(img.width),
            "height": _field(img.height),
            "mode": _field(img.mode),
            "bit_depth": _field(_BITS_PER_CHANNEL.get(img.mode)),  # bits per channel; unknown for unmapped modes
            "icc_profile": _field("embedded") if "icc_profile" in img.info else _field(None, missing=True),
            "exif": exif,
        }
