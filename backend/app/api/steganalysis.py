from typing import Literal

from fastapi import APIRouter
from fastapi.responses import Response

from app.schemas.steganalysis import CoverComparison, CoverComparisonRequest, SteganalysisReport
from app.services import steganalysis

router = APIRouter(prefix="/steganalysis")


@router.get("/report/{image_id}", response_model=SteganalysisReport)
def report(image_id: str) -> SteganalysisReport:
    return steganalysis.report(image_id)


@router.post("/cover-comparison", response_model=CoverComparison)
def cover_comparison(req: CoverComparisonRequest) -> CoverComparison:
    return steganalysis.compare_cover(req.cover_id, req.suspect_id)


@router.get("/lsb-plane/{image_id}/{channel}")
def lsb_plane(image_id: str, channel: Literal["red", "green", "blue"]) -> Response:
    return Response(content=steganalysis.lsb_plane_png(image_id, channel), media_type="image/png")
