"""
Hotspots API Endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.hotspot import HotspotService
from app.schemas.video import HotspotCreate, HotspotFetchRequest, HotspotResponse
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=HotspotResponse)
async def create_hotspot(
    data: HotspotCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new hotspot item"""
    service = HotspotService(db)
    
    # Check for duplicates
    existing = await service.get_by_platform_id(data.platform, data.content_id)
    if existing:
        raise HTTPException(status_code=409, detail="Hotspot already exists")
    
    item = await service.create(data)
    return item


@router.get("", response_model=List[HotspotResponse])
async def list_hotspots(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List hotspot items"""
    service = HotspotService(db)
    items = await service.list_recent(platform=platform, limit=limit)
    return items


@router.get("/search")
async def search_hotspots(
    keyword: str = Query(..., min_length=1, max_length=100),
    platform: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search hotspots by keyword"""
    service = HotspotService(db)
    results = await service.search(keyword=keyword, platform=platform, limit=limit)
    return {"keyword": keyword, "platform": platform, "results": results}


@router.post("/fetch", response_model=List[HotspotResponse])
async def fetch_hotspots(
    data: HotspotFetchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Fetch and persist hotspot items for a given platform and keyword"""
    service = HotspotService(db)
    try:
        items = await service.fetch_hotspots(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return items
