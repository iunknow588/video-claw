"""
Videos API endpoints.
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.db.session import get_db
from departments.CIO.schemas.video import VideoReviewRequest, VideoTaskCreate, VideoTaskResponse
from departments.COO.services.use_cases.video_api import VideoApiUseCase

router = APIRouter()


@router.post("", response_model=VideoTaskResponse)
async def create_video_task(
    data: VideoTaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create video generation task."""
    try:
        return await VideoApiUseCase(db).create_task(data, background_tasks)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get video task status."""
    try:
        return await VideoApiUseCase(db).get_task_status(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/review/{task_id}")
async def review_video_task(
    task_id: str,
    data: VideoReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Review and approve or reject generated video."""
    try:
        return await VideoApiUseCase(db).review_task(
            task_id,
            approved=data.approved,
            feedback=data.feedback,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
async def list_tasks(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List video tasks."""
    return await VideoApiUseCase(db).list_tasks(status=status)
