"""Requests for recorded investigation analyses."""

from pydantic import BaseModel, Field

from app.schemas.evidence import AnalysisType
from app.schemas.watermark import WatermarkMethod


class WatermarkCheck(BaseModel):
    method: WatermarkMethod = "dct"
    key: str = Field(default="", max_length=256, description="Used for extraction only; never recorded.")
    expected_message: str | None = Field(default=None, max_length=64)


class AnalysisRequest(BaseModel):
    type: AnalysisType
    subject_id: str | None = Field(default=None, description="Image to analyse; defaults to the original evidence.")
    reference_id: str | None = Field(
        default=None, description="Comparison: reference image (defaults to the original). Watermark: optional image to report metrics against."
    )
    watermark: WatermarkCheck = Field(default_factory=WatermarkCheck)


class PipelineRequest(BaseModel):
    subject_id: str | None = None
    watermark: WatermarkCheck | None = Field(default=None, description="Include watermark verification with these parameters.")
