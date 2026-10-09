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


class KeyedLSBEmbedRequest(BaseModel):
    evidence_id: str
    payload: str = Field(min_length=1, max_length=100_000)
    key: str = Field(min_length=1, max_length=256)
    bits_per_channel: int = Field(default=1, ge=1, le=1)


class KeyedLSBExtractRequest(BaseModel):
    source_id: str
    key: str = Field(min_length=1, max_length=256)


class LSBMatchingEmbedRequest(BaseModel):
    evidence_id: str
    payload: str = Field(min_length=1, max_length=100_000)
    seed: int = Field(default=0, ge=0, le=2**32 - 1)


class LSBMatchingExtractRequest(BaseModel):
    source_id: str
    payload_bytes: int = Field(ge=1, le=100_000)
    seed: int = Field(default=0, ge=0, le=2**32 - 1)


class SPAEvaluationRequest(BaseModel):
    cover_ids: list[str] = Field(min_length=1, max_length=100)
    stego_ids_by_rate: dict[float, list[str]]
    threshold: float = Field(default=0.05, ge=0, le=1)
