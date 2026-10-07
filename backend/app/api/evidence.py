from urllib.parse import quote

from fastapi import APIRouter, UploadFile
from fastapi.responses import Response

from app.core.config import settings
from app.schemas.evidence import EvidenceArtifact
from app.services import evidence_service
from app.services.store import store

router = APIRouter()


@router.post("/evidence/upload", response_model=EvidenceArtifact, status_code=201)
async def upload(file: UploadFile) -> EvidenceArtifact:
    data = await file.read(settings.max_upload_bytes + 1)
    return evidence_service.ingest(file.filename, data)


@router.get("/evidence", response_model=list[EvidenceArtifact])
def list_evidence() -> list[EvidenceArtifact]:
    return store.list_evidence()


@router.get("/evidence/{evidence_id}", response_model=EvidenceArtifact)
def get_evidence(evidence_id: str) -> EvidenceArtifact:
    return store.evidence(evidence_id)


@router.get("/images/{image_id}")
def get_image(image_id: str, download: bool = False) -> Response:
    """Serve an original or derived image. Bytes are served as an image only, never as HTML."""
    image = store.image(image_id)
    disposition = "attachment" if download else "inline"
    return Response(
        content=image.data,
        media_type=image.mime_type,
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(image.filename)}",
            "X-Content-Type-Options": "nosniff",
        },
    )
