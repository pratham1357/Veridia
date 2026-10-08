from fastapi import APIRouter

from app.schemas.evidence import AnalysisRecord
from app.schemas.investigation import AnalysisRequest, PipelineRequest
from app.services import investigation

router = APIRouter(prefix="/investigation")


@router.post("/{evidence_id}/analyses", response_model=AnalysisRecord)
def run_analysis(evidence_id: str, req: AnalysisRequest) -> AnalysisRecord:
    """Run one analysis on an image of this evidence item and record it."""
    return investigation.run_analysis(evidence_id, req.type, req.subject_id, req.reference_id, req.watermark)


@router.post("/{evidence_id}/pipeline", response_model=list[AnalysisRecord])
def run_pipeline(evidence_id: str, req: PipelineRequest) -> list[AnalysisRecord]:
    """Metadata, integrity, steganalysis, optional watermark verification, and comparison for derived images."""
    return investigation.run_pipeline(evidence_id, req.subject_id, req.watermark)
