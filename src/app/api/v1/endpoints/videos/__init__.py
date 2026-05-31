"""
Videos API Endpoints
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.services.video import VideoService
from app.schemas.video import VideoReviewRequest, VideoTaskCreate, VideoTaskResponse
from app.models.script import Script
from app.models.video import VideoTask
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=VideoTaskResponse)
async def create_video_task(
    data: VideoTaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create video generation task"""
    # Get script
    result = await db.execute(select(Script).where(Script.uuid == data.script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    if script.status != "approved":
        raise HTTPException(status_code=400, detail="Script not approved")
    
    service = VideoService(db)
    task = await service.create_task(
        script=script,
        style=data.style,
        size=data.size,
    )
    
    # Process in background
    background_tasks.add_task(service.process_task, task.uuid)
    
    return task


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get video task status"""
    service = VideoService(db)
    task = await service.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/review/{task_id}")
async def review_video_task(
    task_id: str,
    data: VideoReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Review and approve/reject generated video"""
    service = VideoService(db)
    try:
        task = await service.review_task(task_id, data.approved, data.feedback)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return task


@router.get("")
async def list_tasks(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List video tasks"""
    query = select(VideoTask).order_by(VideoTask.created_at.desc())
    if status:
        query = query.where(VideoTask.status == status)
    result = await db.execute(query)
    return result.scalars().all()
