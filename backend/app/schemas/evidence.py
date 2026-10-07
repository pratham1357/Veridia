"""Evidence model.

Defines the shape of a digital evidence artifact and its provenance chain.
Result fields are indicators/measurements, never authenticity verdicts
(see docs/forensic-philosophy.md).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

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


class FieldStatus(str, Enum):
    available = "available"
    not_available = "not_available"  # the image does not carry this information
    unknown = "unknown"  # may exist but could not be interpreted


class MetadataField(BaseModel):
    status: FieldStatus
    value: str | int | float | None = None


class ExifEntry(BaseModel):
    ifd: str
    tag: str
    value: Any


class ExifBlock(BaseModel):
    status: FieldStatus
    entries: list[ExifEntry] = Field(default_factory=list)


class ImageMetadata(BaseModel):
    format: MetadataField
    width: MetadataField
    height: MetadataField
    mode: MetadataField
    bit_depth: MetadataField = Field(description="Bits per channel as decoded.")
    icc_profile: MetadataField
    exif: ExifBlock


class QualityMetrics(BaseModel):
    mse: float
    psnr_db: float | None = Field(description="None when the images are identical (MSE = 0).")
    ssim: float


class ImageSummary(BaseModel):
    """An image held by the server: the original evidence or a derived artifact."""

    image_id: str
    filename: str
    mime_type: str
    size: int
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    width: int
    height: int


class ProvenanceRecord(BaseModel):
    """One processing step applied to the original evidence."""

    record_id: str
    operation: Literal["lsb_steganography_embed", "watermark_embed"]
    timestamp: datetime
    input_evidence_id: str
    input_sha256: str
    output_image_id: str
    output_sha256: str
    parameters: dict[str, str | int | float | bool] = Field(
        description="Safe parameters only: payloads and keys are never recorded."
    )
    metrics: QualityMetrics


class EvidenceArtifact(BaseModel):
    evidence_id: str
    original_filename: str = Field(description="Sanitized display name; never used as a storage path.")
    file_type: EvidenceFileType
    file_size: int = Field(ge=0, description="Size in bytes.")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    width: int
    height: int
    created_at: datetime = Field(description="Time of intake and analysis (UTC).")

    metadata_results: ImageMetadata | None = None
    integrity_results: FindingSet | None = None
    steganography_results: FindingSet | None = None
    watermark_results: FindingSet | None = None
    provenance: list[ProvenanceRecord] = Field(default_factory=list)
