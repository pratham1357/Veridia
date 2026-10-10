"""Request/response models for watermarking, attack experiments and method comparison."""

from typing import Literal

from pydantic import BaseModel, Field

from analysis.watermarking.robustness import MAX_SWEEP_POINTS
from app.schemas.evidence import ImageSummary, ProvenanceRecord, QualityMetrics

WatermarkMethod = Literal["spatial_lsb", "dct", "dwt"]
VerifyStatus = Literal["verified", "mismatch", "extracted", "not_found"]


class WatermarkEmbedRequest(BaseModel):
    evidence_id: str
    method: WatermarkMethod = "spatial_lsb"
    message: str = Field(min_length=1, max_length=64)
    key: str = Field(default="", max_length=256)
    strength: float | None = Field(default=None, ge=1, le=200, description="Transform-domain methods (DCT, DWT) only.")


class WatermarkVerifyRequest(BaseModel):
    source_id: str
    method: WatermarkMethod = "spatial_lsb"
    key: str = Field(default="", max_length=256)
    expected_message: str | None = Field(default=None, max_length=64)
    reference_id: str | None = Field(default=None, description="Optional original image for comparison.")


class WatermarkVerifyResult(BaseModel):
    method: WatermarkMethod
    status: VerifyStatus
    message: str | None = None
    bit_agreement: float | None = None
    bit_error_rate: float | None = Field(default=None, description="Raw carrier bit errors vs. the expected message.")
    parameters: dict[str, int | float | str]
    reference_metrics: QualityMetrics | None = None
    detail: str


class AttackInfo(BaseModel):
    name: str
    label: str
    parameter_label: str
    presets: list[float]
    minimum: float
    maximum: float


class RobustnessRow(BaseModel):
    attack: str
    attack_label: str
    parameter: float
    parameter_label: str
    mse: float
    psnr_db: float | None
    ssim: float
    status: VerifyStatus
    extracted_message: str | None
    bit_error_rate: float | None


class AttackRequest(BaseModel):
    image_id: str = Field(description="Watermarked image to attack.")
    method: WatermarkMethod
    attack: str
    parameter: float
    message: str = Field(min_length=1, max_length=64, description="Expected watermark message.")
    key: str = Field(default="", max_length=256)


class AttackResult(BaseModel):
    artifact: ImageSummary
    record: ProvenanceRecord
    row: RobustnessRow


class RobustnessRequest(BaseModel):
    image_id: str
    method: WatermarkMethod
    message: str = Field(min_length=1, max_length=64)
    key: str = Field(default="", max_length=256)


class RobustnessReport(BaseModel):
    image_id: str
    method: WatermarkMethod
    rows: list[RobustnessRow]


class SweepRequest(BaseModel):
    """One attack swept across a parameter range, so the point where recovery fails is visible."""

    image_id: str
    method: WatermarkMethod
    message: str = Field(min_length=1, max_length=64)
    key: str = Field(default="", max_length=256)
    attack: str = "jpeg"
    start: float | None = Field(default=None, allow_inf_nan=False, description="Default: the attack's own sweep range (JPEG: 10).")
    stop: float | None = Field(default=None, allow_inf_nan=False, description="Default: the attack's own sweep range (JPEG: 100).")
    step: float | None = Field(
        default=None, gt=0, allow_inf_nan=False,
        description=f"Default: the attack's own sweep range (JPEG: 10). At most {MAX_SWEEP_POINTS} points per series "
                    "((stop - start) / step + 1); the range itself is limited by the attack.",
    )
    methods: list[WatermarkMethod] | None = Field(
        default=None, description="Sweep these methods instead of `method`; each is embedded fresh from the same evidence."
    )


class SweepSeries(BaseModel):
    method: WatermarkMethod
    image_id: str
    rows: list[RobustnessRow]


class SweepReport(BaseModel):
    attack: str
    attack_label: str
    parameter_label: str
    series: list[SweepSeries]


class CompareMethodsRequest(BaseModel):
    evidence_id: str
    message: str = Field(min_length=1, max_length=16, description="Must fit every scheme (DCT and DWT: 16 bytes).")
    key: str = Field(default="", max_length=256)
    strength: float | None = Field(
        default=None, ge=1, le=200,
        description="DCT strength only. DWT and spatial always use their documented defaults, because DCT and DWT "
                    "strengths are on different scales.",
    )


class MethodComparison(BaseModel):
    method: WatermarkMethod
    artifact: ImageSummary
    record: ProvenanceRecord
    verification: WatermarkVerifyResult
    robustness: list[RobustnessRow]


class CompareMethodsResult(BaseModel):
    original: ImageSummary
    methods: list[MethodComparison]
