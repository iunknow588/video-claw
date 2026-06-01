from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.CIO.models.script import Script
from app.CIO.schemas.video import ScriptCreate
from app.CIO.services.data_access.analysis_repository import AnalysisRepository
from app.COO.services.script_management import ScriptService


class ScriptApiUseCase:
    """API-facing script use case owned by COO."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.analysis_repository = AnalysisRepository(session)
        self.script_service = ScriptService(session)

    async def create_script(self, data: ScriptCreate) -> Script:
        analysis = await self.analysis_repository.get_by_uuid(data.analysis_id)
        if not analysis:
            raise LookupError("Analysis not found")

        return await self.script_service.generate_script(
            analysis=analysis,
            content_type=data.content_type,
            style=data.style,
            topic=data.topic,
            duration=data.duration,
        )

    async def list_scripts(self, *, status: str | None) -> list[Script]:
        query = select(Script).order_by(Script.created_at.desc())
        if status:
            query = query.where(Script.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def review_script(self, script_id: str, *, approved: bool, feedback: str) -> Script:
        try:
            return await self.script_service.review_script(script_id, approved, feedback)
        except ValueError as exc:
            if "not found" in str(exc).lower():
                raise LookupError(str(exc)) from exc
            raise
