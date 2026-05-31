from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.video import DomainWorkflowRequest
from app.services.orchestration import WorkflowAssembly, WorkflowExecutionEngine, WorkflowExecutionRecorder

WorkflowEventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class SkillWorkflowOrchestrator:
    """Backward-compatible facade around the split workflow assembly/execution/recording stack."""

    def __init__(self, session: AsyncSession):
        self.assembly = WorkflowAssembly(session)
        self.recorder = WorkflowExecutionRecorder(self.assembly)
        self.engine = WorkflowExecutionEngine(self.assembly, self.recorder)

    async def run_domain_workflow(
        self,
        request: DomainWorkflowRequest,
        *,
        event_callback: WorkflowEventCallback | None = None,
    ) -> dict[str, Any]:
        return await self.engine.run_domain_workflow(request, event_callback=event_callback)
