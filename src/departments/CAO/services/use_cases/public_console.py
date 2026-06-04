from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from departments.CAO.service import CAOConsoleService


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

    async def get_identity_settings(self) -> dict:
        return await self.service.get_identity_settings()

    async def update_identity_settings(self, names: dict) -> dict:
        return await self.service.update_identity_settings(names)

    async def get_system_settings(self) -> dict:
        return await self.service.get_system_settings()

    async def update_identity_profile(self, *, console_title: str | None, names: dict) -> dict:
        return await self.service.update_identity_profile(console_title=console_title, names=names)

    async def get_ceo_runtime_settings(self) -> dict:
        return await self.service.get_ceo_runtime_settings()

    async def update_ceo_runtime_settings(self, updates: dict) -> dict:
        return await self.service.update_ceo_runtime_settings(updates)

    async def get_api_provider_settings(self) -> dict:
        return await self.service.get_api_provider_settings()

    async def update_api_provider_settings(self, updates: dict) -> dict:
        return await self.service.update_api_provider_settings(updates)
