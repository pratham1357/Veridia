from typing import Literal

from fastapi import APIRouter
from fastapi.responses import Response

from app.schemas.evidence import ReportRecord
from app.services import reports
from app.services.store import REPORT_FORMATS, store

router = APIRouter(prefix="/reports")

# The HTML report needs no scripts, frames or remote resources; forbid them.
REPORT_CSP = "default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"


@router.post("/{evidence_id}", response_model=ReportRecord, status_code=201)
def create(evidence_id: str) -> ReportRecord:
    """Generate the JSON and HTML investigation report and record the export in the timeline."""
    return reports.create_report(evidence_id)


@router.get("/{evidence_id}", response_model=list[ReportRecord])
def list_reports(evidence_id: str) -> list[ReportRecord]:
    return store.evidence(evidence_id).reports


@router.get("/{evidence_id}/{report_id}/{fmt}")
def download(evidence_id: str, report_id: str, fmt: Literal["json", "html"], download: bool = False) -> Response:
    data, record = reports.report_file(evidence_id, report_id, fmt)
    disposition = "attachment" if download else "inline"
    return Response(
        content=data,
        media_type=f"{REPORT_FORMATS[fmt]}; charset=utf-8",
        headers={
            "Content-Disposition": f'{disposition}; filename="veridia_{report_id}.{fmt}"',
            "Content-Security-Policy": REPORT_CSP,
            "X-Content-Type-Options": "nosniff",
            "X-Report-SHA256": record.json_sha256 if fmt == "json" else record.html_sha256,
        },
    )
