from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.schemas.video import DomainWorkflowRequest
from departments.CEO.services.orchestration.assembly import WorkflowAssembly
from departments.CEO.services.orchestration.engine import WorkflowExecutionEngine
from departments.CEO.services.orchestration.recorder import WorkflowRecorder

WorkflowEventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class DomainWorkflowService:
    """Workflow facade owned by CEO orchestration."""

    def __init__(self, session: AsyncSession):
        assembly = WorkflowAssembly(session)
        recorder = WorkflowRecorder(assembly)
        self.engine = WorkflowExecutionEngine(assembly, recorder)

    async def run(
        self,
        request: DomainWorkflowRequest,
        *,
        event_callback: WorkflowEventCallback | None = None,
    ) -> dict[str, object]:
        return await self.engine.run_domain_workflow(request, event_callback=event_callback)
