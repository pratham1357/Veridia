from fastapi import APIRouter

from app.api import analysis, evidence, health, investigation, provenance, reports, steganalysis, steganography, watermark

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router, tags=["system"])
api_router.include_router(evidence.router, tags=["evidence"])
api_router.include_router(steganography.router, tags=["steganography"])
api_router.include_router(steganalysis.router, tags=["steganalysis"])
api_router.include_router(watermark.router, tags=["watermarking"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(investigation.router, tags=["investigation"])
api_router.include_router(provenance.router, tags=["provenance"])
api_router.include_router(reports.router, tags=["reports"])
