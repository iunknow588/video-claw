"""
Images API endpoints.
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.db.session import get_db
from departments.CIO.schemas.video import ImageTaskCreate, ImageTaskResponse
from departments.COO.services.use_cases.image_api import ImageApiUseCase

router = APIRouter()


@router.post("", response_model=ImageTaskResponse)
async def create_image_task(
    data: ImageTaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await ImageApiUseCase(db).create_task(data, background_tasks)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/task/{task_id}", response_model=ImageTaskResponse)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await ImageApiUseCase(db).get_task_status(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=list[ImageTaskResponse])
async def list_tasks(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await ImageApiUseCase(db).list_tasks(status=status)
