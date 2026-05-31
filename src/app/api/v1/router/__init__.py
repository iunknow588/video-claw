"""
API Router - V1
"""

from fastapi import APIRouter

from app.api.v1.endpoints import analysis, cao, ceo, cmo, hotspots, operations, promotion, scripts, videos, workflows

api_router = APIRouter()

api_router.include_router(hotspots.router, prefix="/hotspots", tags=["hotspots"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(scripts.router, prefix="/scripts", tags=["scripts"])
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(operations.router, prefix="/operations", tags=["operations"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(cao.router, prefix="/cao", tags=["cao"])
api_router.include_router(cmo.router, prefix="/cmo", tags=["cmo"])
api_router.include_router(ceo.router, prefix="/ceo", tags=["ceo"])
api_router.include_router(promotion.router, prefix="/promotion", tags=["promotion"])
