"""
Hotspots API endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.CIO.db.session import get_db
from app.CIO.schemas.video import HotspotCreate, HotspotFetchRequest, HotspotResponse
from app.CSO.services.use_cases.hotspot_api import HotspotApiUseCase

router = APIRouter()


@router.post("", response_model=HotspotResponse)
async def create_hotspot(
    data: HotspotCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new hotspot item."""
    try:
        return await HotspotApiUseCase(db).create_hotspot(data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("", response_model=List[HotspotResponse])
async def list_hotspots(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List hotspot items."""
    return await HotspotApiUseCase(db).list_hotspots(platform=platform, limit=limit)


@router.get("/search")
async def search_hotspots(
    keyword: str = Query(..., min_length=1, max_length=100),
    platform: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search hotspots by keyword."""
    return await HotspotApiUseCase(db).search_hotspots(
        keyword=keyword,
        platform=platform,
        limit=limit,
    )


@router.post("/fetch", response_model=List[HotspotResponse])
async def fetch_hotspots(
    data: HotspotFetchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Fetch and persist hotspot items for a given platform and keyword."""
    try:
        return await HotspotApiUseCase(db).fetch_hotspots(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
