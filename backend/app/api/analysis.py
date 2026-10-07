from fastapi import APIRouter

from app.schemas.operations import CompareRequest, CompareResult
from app.services import operations

router = APIRouter(prefix="/analysis")


@router.post("/compare", response_model=CompareResult)
def compare(req: CompareRequest) -> CompareResult:
    return operations.compare(req.original_id, req.processed_id)
