from __future__ import annotations

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from departments.CIO.models.image import ImageTask
from departments.CIO.models.script import Script
from departments.CIO.schemas.video import ImageTaskCreate
from departments.COO.services.asset_management import ImageGenerationService


def _build_session_factory(session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    bind = session.bind
    if bind is None:
        raise RuntimeError("Background image task requires an active session bind")
    return async_sessionmaker(bind, expire_on_commit=False, class_=AsyncSession)


async def _process_image_task_in_background(
    task_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        try:
            await ImageGenerationService(session).process_task(task_id)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class ImageApiUseCase:
    """API-facing image generation use case owned by COO."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.image_service = ImageGenerationService(session)

    async def create_task(self, data: ImageTaskCreate, background_tasks: BackgroundTasks) -> ImageTask:
        if data.script_id:
            result = await self.session.execute(select(Script).where(Script.uuid == data.script_id))
            script = result.scalar_one_or_none()
            if not script:
                raise LookupError("Script not found")

        task = await self.image_service.create_task(
            script_id=data.script_id,
            prompt=data.prompt,
            negative_prompt=data.negative_prompt,
            aspect_ratio=data.aspect_ratio,
            resolution=data.resolution,
            image_count=data.image_count,
            use_case=data.use_case,
        )
        await self.session.commit()
        await self.session.refresh(task)
        background_tasks.add_task(
            _process_image_task_in_background,
            task.uuid,
            _build_session_factory(self.session),
        )
        return task

    async def get_task_status(self, task_id: str) -> ImageTask:
        task = await self.image_service.get_task_status(task_id)
        if not task:
            raise LookupError("Task not found")
        return task

    async def list_tasks(self, *, status: str | None) -> list[ImageTask]:
        query = select(ImageTask).order_by(ImageTask.created_at.desc())
        if status:
            query = query.where(ImageTask.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())
