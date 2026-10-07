"""Request/response models for the steganography, watermarking and comparison endpoints."""

from typing import Literal

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


class ChannelLsbStats(BaseModel):
    channel: Literal["red", "green", "blue"]
    ones_ratio: float
    transition_ratio: float


class LsbAnalysis(BaseModel):
    image_id: str
    channels: list[ChannelLsbStats]
    veridia_lsb_header_found: bool
    note: str


class WatermarkEmbedRequest(BaseModel):
    evidence_id: str
    message: str = Field(min_length=1, max_length=64)
    key: str = Field(default="", max_length=256)


class WatermarkVerifyRequest(BaseModel):
    source_id: str
    key: str = Field(default="", max_length=256)
    expected_message: str | None = Field(default=None, max_length=64)


class WatermarkVerifyResult(BaseModel):
    status: Literal["verified", "mismatch", "extracted", "not_found"]
    message: str | None = None
    bit_agreement: float | None = None
    detail: str


class CompareRequest(BaseModel):
    original_id: str
    processed_id: str


class CompareResult(BaseModel):
    original: ImageSummary
    processed: ImageSummary
    metrics: QualityMetrics
    hashes_differ: bool
