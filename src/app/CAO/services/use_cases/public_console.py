from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.CAO.service import CAOConsoleService


class PublicConsoleUseCase:
    """API-facing public console use case owned by CAO."""

    def __init__(self, session: AsyncSession):
        self.service = CAOConsoleService(session)

    async def get_pipeline_status(self) -> dict:
        return await self.service.get_pipeline_status()

    async def list_public_runs(
        self,
        *,
        limit: int,
        domain: str | None,
        platform: str | None,
        status: str | None,
    ) -> list[dict]:
        return await self.service.list_public_runs(
            limit=limit,
            domain=domain,
            platform=platform,
            status=status,
        )

    async def get_public_trace(self, workflow_run_id: str) -> dict:
        try:
            return await self.service.get_public_trace(workflow_run_id)
        except ValueError as exc:
            raise LookupError(str(exc)) from exc
