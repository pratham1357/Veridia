from fastapi import APIRouter
from fastapi.responses import Response

from app.schemas.operations import CompareRequest, CompareResult
from app.services import operations

router = APIRouter(prefix="/analysis")


@router.post("/compare", response_model=CompareResult)
def compare(req: CompareRequest) -> CompareResult:
    return operations.compare(req.original_id, req.processed_id)


@router.get("/difference/{original_id}/{processed_id}")
def difference(original_id: str, processed_id: str) -> Response:
    """Stretched absolute-difference image; ``X-Max-Difference`` gives the unstretched peak."""
    png, peak = operations.difference_png(original_id, processed_id)
    return Response(content=png, media_type="image/png", headers={"X-Max-Difference": str(peak)})
