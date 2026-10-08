from fastapi import APIRouter

from app.schemas.operations import (
    CapacityReport,
    OperationResult,
    StegoEmbedRequest,
    StegoExtractRequest,
    StegoExtractResult,
)
from app.services import operations

router = APIRouter(prefix="/steganography")


@router.get("/capacity/{evidence_id}", response_model=CapacityReport)
def capacity(evidence_id: str, payload_bytes: int = 0) -> CapacityReport:
    return operations.stego_capacity(evidence_id, payload_bytes)


@router.post("/embed", response_model=OperationResult)
def embed(req: StegoEmbedRequest) -> OperationResult:
    return operations.embed_stego(req.evidence_id, req.payload)


@router.post("/extract", response_model=StegoExtractResult)
def extract(req: StegoExtractRequest) -> StegoExtractResult:
    return operations.extract_stego(req.source_id)
