from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.schemas.video import DomainWorkflowRequest
from departments.CIO.services.event_bus import WorkflowEventCallback
from departments.CEO.services.orchestration.assembly import WorkflowAssembly
from departments.CEO.services.orchestration.engine import WorkflowExecutionEngine
from departments.CEO.services.orchestration.recorder import WorkflowRecorder


class DomainWorkflowService:
    """Workflow facade owned by CEO orchestration."""

    def __init__(self, session: AsyncSession):
        self.assembly = WorkflowAssembly(session)
        self.assembly.recorder = WorkflowRecorder(self.assembly)
        self.engine = WorkflowExecutionEngine(self.assembly)

    async def run(
        self,
        request: DomainWorkflowRequest,
        *,
        event_callback: WorkflowEventCallback | None = None,
    ) -> dict[str, object]:
        return await self.engine.run_domain_workflow(
            request,
            event_callback=event_callback,
        )
