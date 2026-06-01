from __future__ import annotations

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.models.script import Script
from departments.CIO.models.video import VideoTask
from departments.CIO.schemas.video import VideoTaskCreate
from departments.COO.services.video_production import VideoService


class VideoApiUseCase:
    """API-facing video use case owned by COO."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.video_service = VideoService(session)

    async def create_task(self, data: VideoTaskCreate, background_tasks: BackgroundTasks) -> VideoTask:
        result = await self.session.execute(select(Script).where(Script.uuid == data.script_id))
        script = result.scalar_one_or_none()
        if not script:
            raise LookupError("Script not found")
        if script.status != "approved":
            raise ValueError("Script not approved")

        task = await self.video_service.create_task(
            script=script,
            style=data.style,
            size=data.size,
        )
        background_tasks.add_task(self.video_service.process_task, task.uuid)
        return task

    async def get_task_status(self, task_id: str) -> VideoTask:
        task = await self.video_service.get_task_status(task_id)
        if not task:
            raise LookupError("Task not found")
        return task

    async def review_task(self, task_id: str, *, approved: bool, feedback: str) -> VideoTask:
        try:
            return await self.video_service.review_task(task_id, approved, feedback)
        except ValueError as exc:
            if "not found" in str(exc).lower():
                raise LookupError(str(exc)) from exc
            raise

    async def list_tasks(self, *, status: str | None) -> list[VideoTask]:
        query = select(VideoTask).order_by(VideoTask.created_at.desc())
        if status:
            query = query.where(VideoTask.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())
