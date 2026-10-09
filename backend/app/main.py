from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.services.errors import ServiceError
from app.services.store import store


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Load persisted evidence from ``storage/`` (or run memory-only when VERIDIA_PERSIST=false)."""
    store.open(settings.storage_dir if settings.persist else None)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="VERIDIA API",
        description="Digital Image Provenance & Forensics Workbench",
        version=settings.version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.exception_handler(ServiceError)
    async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(api_router)
    return app


app = create_app()
