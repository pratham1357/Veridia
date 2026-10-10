from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
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

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # The default body echoes each rejected value under "input". A NaN or Infinity cannot be encoded as
        # JSON, so the error response itself crashed (HTTP 500) exactly when a non-finite number was rejected.
        errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})

    app.include_router(api_router)
    return app


app = create_app()
