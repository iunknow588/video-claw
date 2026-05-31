from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.video import DomainWorkflowRequest
from app.skills.workflow_orchestrator import SkillWorkflowOrchestrator

WorkflowEventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class DomainWorkflowService:
    """Compatibility adapter that delegates to the skill workflow orchestrator."""

    def __init__(self, session: AsyncSession):
        self.orchestrator = SkillWorkflowOrchestrator(session)

    async def run(
        self,
        request: DomainWorkflowRequest,
        *,
        event_callback: WorkflowEventCallback | None = None,
    ) -> dict[str, object]:
        return await self.orchestrator.run_domain_workflow(request, event_callback=event_callback)
