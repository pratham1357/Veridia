from fastapi import APIRouter, Query

from app.schemas.provenance import ChainVerification, OperationInfo
from app.services import operation_registry, provenance
from app.services.store import store

router = APIRouter(prefix="/provenance")


@router.get("/operations", response_model=list[OperationInfo])
def operations() -> list[OperationInfo]:
    """Registered image-producing operations (names, labels, categories)."""
    return operation_registry.operations()


@router.get("/{evidence_id}/verify", response_model=ChainVerification)
def verify(
    evidence_id: str,
    expected_head: str | None = Query(default=None, pattern=r"^[0-9a-fA-F]{64}$", description="A head hash recorded earlier, e.g. from a report."),
) -> ChainVerification:
    """Recompute the timeline hash chain, the records it covers and the hashes of all stored files. Read-only."""
    return provenance.verify(store.evidence(evidence_id), expected_head.lower() if expected_head else None)
