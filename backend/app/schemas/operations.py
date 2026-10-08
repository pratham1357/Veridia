"""Request/response models for the steganography and comparison endpoints."""

from pydantic import BaseModel, Field

from app.schemas.evidence import ImageSummary, ProvenanceRecord, QualityMetrics


class CapacityReport(BaseModel):
    capacity_bytes: int
    payload_bytes: int
    utilization_percent: float


class OperationResult(BaseModel):
    artifact: ImageSummary
    record: ProvenanceRecord
    capacity: CapacityReport | None = None


class StegoEmbedRequest(BaseModel):
    evidence_id: str
    payload: str = Field(min_length=1, max_length=100_000)


class StegoExtractRequest(BaseModel):
    source_id: str = Field(description="Evidence or artifact ID to extract from.")


class StegoExtractResult(BaseModel):
    found: bool
    payload: str | None = None
    payload_bytes: int | None = None
    detail: str


class CompareRequest(BaseModel):
    original_id: str
    processed_id: str


class CompareResult(BaseModel):
    original: ImageSummary
    processed: ImageSummary
    metrics: QualityMetrics
    hashes_differ: bool
