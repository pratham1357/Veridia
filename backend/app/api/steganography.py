from fastapi import APIRouter

from app.schemas.operations import (
    CapacityReport,
    OperationResult,
    StegoEmbedRequest,
    StegoExtractRequest,
    StegoExtractResult,
    KeyedLSBEmbedRequest,
    KeyedLSBExtractRequest,
    LSBMatchingEmbedRequest,
    LSBMatchingExtractRequest,
    SPAEvaluationRequest,
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


@router.post("/keyed-lsb/embed", response_model=OperationResult)
def embed_keyed(req: KeyedLSBEmbedRequest) -> OperationResult:
    return operations.embed_keyed_lsb(
        req.evidence_id, req.payload, req.key
    )


@router.post("/keyed-lsb/extract", response_model=StegoExtractResult)
def extract_keyed(req: KeyedLSBExtractRequest) -> StegoExtractResult:
    return operations.extract_keyed_lsb(req.source_id, req.key)


@router.post("/lsb-matching/embed", response_model=OperationResult)
def embed_matching(req: LSBMatchingEmbedRequest) -> OperationResult:
    return operations.embed_lsb_matching(
        req.evidence_id, req.payload, req.seed
    )


@router.post("/lsb-matching/extract", response_model=StegoExtractResult)
def extract_matching(req: LSBMatchingExtractRequest) -> StegoExtractResult:
    return operations.extract_lsb_matching(
        req.source_id, req.payload_bytes, req.seed
    )


@router.post("/spa/evaluate")
def evaluate_spa_endpoint(req: SPAEvaluationRequest) -> dict:
    return operations.evaluate_spa(
        req.cover_ids, req.stego_ids_by_rate, req.threshold
    )
