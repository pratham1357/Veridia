"""Evidence model.

An ``EvidenceArtifact`` is the investigator's record for one uploaded image:
its identity and metadata, every derived artifact produced from it (with parent
links and hashes), every processing operation, every recorded analysis result
and a chronological timeline of what the application actually did. Analysis
results are measurements and findings, never authenticity verdicts
(see docs/forensic-philosophy.md).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceFileType(BaseModel):
    mime_type: str = Field(description="Detected from file signature, not from the client-supplied header.")
    extension: str | None = None


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
    """One processing step applied to the evidence or to an image derived from it."""

    record_id: str
    operation: Literal[
        "lsb_steganography_embed",
        "keyed_lsb_steganography_embed",
        "lsb_matching_steganography_embed",
        "watermark_embed",
        "dct_watermark_embed",
        "attack",
    ]
    timestamp: datetime
    input_evidence_id: str = Field(description="Root evidence this processing chain belongs to.")
    input_image_id: str = Field(description="The image actually processed: the evidence or a derived artifact.")
    input_sha256: str
    output_image_id: str
    output_sha256: str
    parameters: dict[str, str | int | float | bool] = Field(
        description="Safe parameters only: payloads and keys are never recorded."
    )
    metrics: QualityMetrics


AnalysisType = Literal["metadata", "integrity", "steganalysis", "watermark", "comparison"]
AnalysisStatus = Literal["verified", "indicator_detected", "no_indicator", "inconclusive", "not_applicable"]


class Finding(BaseModel):
    finding: str
    evidence: str = Field(description="The measurement supporting the finding.")
    interpretation: str = Field(description="What the measurement may indicate.")
    limitation: str = Field(description="What the finding does NOT establish.")
    kind: Literal["observation", "indicator", "verification"]


class AnalysisResult(BaseModel):
    """Common result structure returned by every analysis module (mirrors analysis.core.AnalysisResult)."""

    analysis_type: AnalysisType
    analyzer_version: str
    status: AnalysisStatus
    interpretation: str
    measurements: dict[str, str | int | float | bool | None]
    findings: list[Finding]
    limitations: list[str]
    data: dict[str, Any] = Field(default_factory=dict, description="Structured output for visualisation (histograms, tables).")
    timestamp: datetime


class AnalysisRecord(BaseModel):
    """An analysis that was run on a specific image, recorded on the evidence."""

    record_id: str
    subject_image_id: str
    subject_sha256: str
    reference_image_id: str | None = None
    result: AnalysisResult


class DerivedArtifact(BaseModel):
    """An image produced by an operation. Never replaces the original evidence."""

    artifact_id: str
    parent_image_id: str = Field(description="Evidence or artifact this was derived from.")
    parent_sha256: str
    operation: str
    created_at: datetime
    filename: str
    mime_type: str
    size: int
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    width: int
    height: int
    provenance_record_id: str


class TimelineEvent(BaseModel):
    """Something the application actually did, in the order it happened."""

    event_id: str
    timestamp: datetime
    event_type: Literal["evidence_acquired", "metadata_extracted", "hash_computed", "artifact_created", "analysis_completed"]
    subject_image_id: str
    description: str
    reference_id: str | None = Field(default=None, description="Related provenance or analysis record.")


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
    provenance: list[ProvenanceRecord] = Field(default_factory=list, description="Image-producing operations.")
    derived_artifacts: list[DerivedArtifact] = Field(default_factory=list)
    analyses: list[AnalysisRecord] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
