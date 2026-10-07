"""Evidence ingestion: validate untrusted uploads, hash them, and record the original."""

import re
import uuid
from datetime import datetime, timezone

from analysis.core import ImageDecodeError, decode_rgb, probe, sha256_hex
from analysis.metadata import extract_metadata
from app.core.config import settings
from app.schemas.evidence import EvidenceArtifact, EvidenceFileType, ImageMetadata
from app.services.errors import ServiceError
from app.services.store import StoredImage, store

_SIGNATURES = (("PNG", b"\x89PNG\r\n\x1a\n"), ("JPEG", b"\xff\xd8\xff"), ("BMP", b"BM"))
_FORMATS = {"PNG": ("image/png", {"png"}), "JPEG": ("image/jpeg", {"jpg", "jpeg"}), "BMP": ("image/bmp", {"bmp"})}


def sanitize_filename(name: str | None) -> str:
    """Display-only filename: no directory components, restricted characters, bounded length."""
    base = re.split(r"[\\/]", name or "")[-1]
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(" .")
    return base[:100] or "upload"


def _detect_format(data: bytes) -> str | None:
    return next((fmt for fmt, magic in _SIGNATURES if data.startswith(magic)), None)


def ingest(filename: str | None, data: bytes) -> EvidenceArtifact:
    if not data:
        raise ServiceError("Uploaded file is empty.", 400)
    if len(data) > settings.max_upload_bytes:
        raise ServiceError(f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit.", 413)

    safe_name = sanitize_filename(filename)
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    fmt = _detect_format(data)
    if fmt is None:
        raise ServiceError("Unsupported file type. Supported formats: PNG, JPEG, BMP.", 415)
    mime, extensions = _FORMATS[fmt]
    if ext not in extensions:
        raise ServiceError("File extension does not match the file's actual content.", 415)

    try:
        probed_format, width, height = probe(data)
        if probed_format != fmt:
            raise ServiceError("File content does not match its signature.", 415)
        if width * height > settings.max_pixels:
            raise ServiceError(f"Image exceeds the {settings.max_pixels:,} pixel limit.", 413)
        decode_rgb(data)  # full decode: rejects truncated/corrupt files up front
        metadata = ImageMetadata.model_validate(extract_metadata(data))
    except ImageDecodeError as exc:
        raise ServiceError(str(exc), 400) from exc

    digest = sha256_hex(data)
    evidence_id = f"ev_{uuid.uuid4().hex}"
    evidence = EvidenceArtifact(
        evidence_id=evidence_id,
        original_filename=safe_name,
        file_type=EvidenceFileType(mime_type=mime, extension=ext),
        file_size=len(data),
        sha256=digest,
        width=width,
        height=height,
        created_at=datetime.now(timezone.utc),
        metadata_results=metadata,
    )
    original = StoredImage(evidence_id, safe_name, mime, data, digest, width, height)
    store.add_evidence(evidence, original)
    return evidence
