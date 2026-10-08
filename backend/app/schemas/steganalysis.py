"""Response models for steganalysis. All values are measurements or potential indicators."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.evidence import ImageSummary

Channel = Literal["red", "green", "blue"]


class RsStats(BaseModel):
    r_m: float | None
    s_m: float | None
    r_neg_m: float | None
    s_neg_m: float | None
    estimate: float | None = Field(description="Estimated fraction of samples carrying embedded bits; None if undefined.")


class ChannelSteganalysis(BaseModel):
    channel: Channel
    mean: float
    std: float
    entropy_bits: float
    ones_ratio: float
    transition_ratio: float
    chi_square_p: float | None
    rs: RsStats


class ChiSquarePoint(BaseModel):
    fraction: float
    p_value: float | None


class ChiSquareResult(BaseModel):
    chi2: float | None
    degrees_of_freedom: int
    p_value: float | None
    curve: list[ChiSquarePoint]
    consistent_prefix_fraction: float


class SteganalysisReport(BaseModel):
    image_id: str
    channels: list[ChannelSteganalysis]
    histograms: dict[Channel, list[int]]
    chi_square: ChiSquareResult
    rs_mean_estimate: float | None
    lsb_capacity_bytes: int
    prefix_payload_bytes_upper: int
    veridia_lsb_header_found: bool
    indicators: list[str]
    disclaimer: str


class CoverComparisonRequest(BaseModel):
    cover_id: str = Field(description="Known cover (original) image.")
    suspect_id: str = Field(description="Suspected stego image.")


class CoverComparison(BaseModel):
    cover: ImageSummary
    suspect: ImageSummary
    total_samples: int
    changed_samples: int
    changed_fraction: float
    max_abs_difference: int
    lsb_only: bool
    changed_per_channel: dict[Channel, int]
    first_changed_index: int | None
    last_changed_index: int | None
