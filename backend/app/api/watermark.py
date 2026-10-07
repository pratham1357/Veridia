from fastapi import APIRouter

from app.schemas.operations import (
    OperationResult,
    WatermarkEmbedRequest,
    WatermarkVerifyRequest,
    WatermarkVerifyResult,
)
from app.services import operations

router = APIRouter(prefix="/watermark")


@router.post("/embed", response_model=OperationResult)
def embed(req: WatermarkEmbedRequest) -> OperationResult:
    return operations.embed_watermark(req.evidence_id, req.message, req.key)


@router.post("/verify", response_model=WatermarkVerifyResult)
def verify(req: WatermarkVerifyRequest) -> WatermarkVerifyResult:
    return operations.verify_watermark(req.source_id, req.key, req.expected_message)
