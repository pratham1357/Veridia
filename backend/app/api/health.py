from fastapi import APIRouter

from app.core.config import settings
from app.services.store import store

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str | int]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.version,
        "storage": "persistent" if store.persistent else "memory",
        "evidence_count": len(store.list_evidence()),
        "storage_load_errors": len(store.load_errors),
    }
