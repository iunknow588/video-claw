from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.video import DomainWorkflowRequest
from app.services.workflow import DomainWorkflowService

PipelineEventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class ProductionPipelineService:
    """Neutral production-pipeline entrypoint for upstream gatekeepers such as finance."""

    def __init__(self, session: AsyncSession):
        self.workflow_service = DomainWorkflowService(session)

    async def run(
        self,
        request: DomainWorkflowRequest,
        *,
        event_callback: PipelineEventCallback | None = None,
    ) -> dict[str, object]:
        return await self.workflow_service.run(request, event_callback=event_callback)
