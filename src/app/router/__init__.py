from fastapi import APIRouter

from app.router.endpoints.analysis import router as analysis_router
from app.router.endpoints.cao import router as cao_router
from app.router.endpoints.cmo import router as cmo_router
from app.router.endpoints.hotspots import router as hotspots_router
from app.router.endpoints.images import router as images_router
from app.router.endpoints.operations import router as operations_router
from app.router.endpoints.scripts import router as scripts_router
from app.router.endpoints.videos import router as videos_router

api_router = APIRouter()
api_router.include_router(hotspots_router, prefix="/hotspots", tags=["hotspots"])
api_router.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
api_router.include_router(scripts_router, prefix="/scripts", tags=["scripts"])
api_router.include_router(images_router, prefix="/images", tags=["images"])
api_router.include_router(videos_router, prefix="/videos", tags=["videos"])
api_router.include_router(operations_router, prefix="/operations", tags=["operations"])
api_router.include_router(cmo_router, prefix="/cmo", tags=["cmo"])
api_router.include_router(cao_router, prefix="/cao", tags=["cao"])

__all__ = ["api_router"]
