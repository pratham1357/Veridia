from fastapi import APIRouter, Query
from fastapi.responses import Response

from analysis.integrity.ela import DEFAULT_QUALITY, MAX_QUALITY, MIN_QUALITY

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


@router.get("/ela/{image_id}")
def ela_map(image_id: str, quality: int = Query(default=DEFAULT_QUALITY, ge=MIN_QUALITY, le=MAX_QUALITY)) -> Response:
    """Stretched error-level image (exploratory, not recorded); ``X-ELA-Peak`` gives the unstretched peak error."""
    png, peak = operations.ela_png(image_id, quality)
    return Response(content=png, media_type="image/png", headers={"X-ELA-Peak": str(peak)})
