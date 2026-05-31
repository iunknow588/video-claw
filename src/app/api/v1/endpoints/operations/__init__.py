"""
Operational summary endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.cost import CostRecord
from app.models.review import ReviewRecord
from app.schemas.video import (
    CostRecordResponse,
    OperationsSummaryResponse,
    ReviewRecordResponse,
    StorageStatusResponse,
)
from app.services.operations import OperationsService
from app.services.storage import describe_video_storage

router = APIRouter()


@router.get("/summary", response_model=OperationsSummaryResponse)
async def get_operations_summary(
    db: AsyncSession = Depends(get_db),
):
    """Return MVP-level counts, status breakdown, and cost summary."""
    service = OperationsService(db)
    return await service.build_summary()


@router.get("/reviews", response_model=List[ReviewRecordResponse])
async def list_reviews(
    item_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List review records for scripts and videos."""
    query = select(ReviewRecord).order_by(ReviewRecord.created_at.desc()).limit(limit)
    if item_type:
        query = query.where(ReviewRecord.item_type == item_type)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/costs", response_model=List[CostRecordResponse])
async def list_costs(
    source_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List cost records across analysis, script, and video stages."""
    query = select(CostRecord).order_by(CostRecord.created_at.desc()).limit(limit)
    if source_type:
        query = query.where(CostRecord.source_type == source_type)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/storage", response_model=StorageStatusResponse)
async def get_storage_status():
    """Return the active video storage backend and sanitized config status."""
    return describe_video_storage()
