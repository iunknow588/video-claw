"""
Operational summary endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.db.session import get_db
from departments.CIO.schemas.video import (
    CostRecordResponse,
    OperationsSummaryResponse,
    ReviewRecordResponse,
    StorageStatusResponse,
)
from departments.CIO.services.use_cases.operations_query import OperationsQueryUseCase

router = APIRouter()


@router.get("/summary", response_model=OperationsSummaryResponse)
async def get_operations_summary(
    db: AsyncSession = Depends(get_db),
):
    return await OperationsQueryUseCase(db).build_summary()


@router.get("/reviews", response_model=List[ReviewRecordResponse])
async def list_reviews(
    item_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await OperationsQueryUseCase(db).list_reviews(item_type=item_type, limit=limit)


@router.get("/costs", response_model=List[CostRecordResponse])
async def list_costs(
    source_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await OperationsQueryUseCase(db).list_costs(source_type=source_type, limit=limit)


@router.get("/storage", response_model=StorageStatusResponse)
async def get_storage_status(
    db: AsyncSession = Depends(get_db),
):
    return OperationsQueryUseCase(db).get_storage_status()
