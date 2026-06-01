from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from departments.CEO.services.orchestration.domain_workflow import DomainWorkflowService
from departments.CIO.schemas.video import DomainWorkflowRequest

PipelineEventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class ScriptToPublishUseCase:
    """COO-owned entry use case for launching the end-to-end script-to-publish workflow."""

    def __init__(self, session: AsyncSession):
        self.workflow_service = DomainWorkflowService(session)

    async def run(
        self,
        request: DomainWorkflowRequest,
        *,
        event_callback: PipelineEventCallback | None = None,
    ) -> dict[str, object]:
        return await self.workflow_service.run(request, event_callback=event_callback)
