"""Foundational evidence model.

Defines the shape of a digital evidence artifact only. There is no persistence
and no analysis behaviour. Result fields are optional until the corresponding
analyzer exists; each carries indicators, never a verdict (see docs/forensic-philosophy.md).
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EvidenceFileType(BaseModel):
    mime_type: str = Field(description="Detected from file signature, not from the client-supplied header.")
    extension: str | None = None


class FindingSet(BaseModel):
    """Container for the output of one analysis module. Structure is defined per module later."""

    analyzer: str
    analyzer_version: str
    indicators: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class EvidenceArtifact(BaseModel):
    evidence_id: str
    original_filename: str = Field(description="Sanitized display name; never used as a storage path.")
    file_type: EvidenceFileType
    file_size: int = Field(ge=0, description="Size in bytes.")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime = Field(description="Time of intake (UTC).")

    metadata_results: FindingSet | None = None
    integrity_results: FindingSet | None = None
    steganography_results: FindingSet | None = None
    watermark_results: FindingSet | None = None
    provenance_results: FindingSet | None = None
