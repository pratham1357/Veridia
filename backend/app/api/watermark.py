from fastapi import APIRouter
from fastapi.responses import Response

from app.schemas.operations import OperationResult
from app.schemas.watermark import (
    AttackInfo,
    AttackRequest,
    AttackResult,
    CompareMethodsRequest,
    CompareMethodsResult,
    RobustnessReport,
    RobustnessRequest,
    SweepReport,
    SweepRequest,
    WatermarkEmbedRequest,
    WatermarkVerifyRequest,
    WatermarkVerifyResult,
)
from app.services import watermarking

router = APIRouter(prefix="/watermark")


@router.post("/embed", response_model=OperationResult)
def embed(req: WatermarkEmbedRequest) -> OperationResult:
    return watermarking.embed(req.evidence_id, req.method, req.message, req.key, req.strength)


@router.post("/verify", response_model=WatermarkVerifyResult)
def verify(req: WatermarkVerifyRequest) -> WatermarkVerifyResult:
    return watermarking.verify(req.source_id, req.method, req.key, req.expected_message, req.reference_id)


@router.get("/attacks", response_model=list[AttackInfo])
def attacks() -> list[AttackInfo]:
    return watermarking.attacks()


@router.post("/attack", response_model=AttackResult)
def attack(req: AttackRequest) -> AttackResult:
    return watermarking.run_attack(req.image_id, req.method, req.attack, req.parameter, req.message, req.key)


@router.post("/robustness", response_model=RobustnessReport)
def robustness(req: RobustnessRequest) -> RobustnessReport:
    return watermarking.run_suite(req.image_id, req.method, req.message, req.key)


@router.post("/compare-methods", response_model=CompareMethodsResult)
def compare_methods(req: CompareMethodsRequest) -> CompareMethodsResult:
    return watermarking.compare_methods(req.evidence_id, req.message, req.key, req.strength)


@router.post("/sweep", response_model=SweepReport)
def sweep(req: SweepRequest) -> SweepReport:
    """Run one attack across a parameter range (default: JPEG quality 10-100)."""
    return watermarking.sweep(req)


@router.get("/dwt-map/{image_id}")
def dwt_map(image_id: str) -> Response:
    """The four one-level Haar sub-bands tiled as LL/LH over HL/HH."""
    return Response(content=watermarking.dwt_map_png(image_id), media_type="image/png")


@router.get("/dct-map/{image_id}")
def dct_map(image_id: str) -> Response:
    return Response(content=watermarking.dct_map_png(image_id), media_type="image/png")
