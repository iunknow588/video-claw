from __future__ import annotations

from typing import Any

from departments.CIO.services.workflow_steps import WorkflowStepLogService


class TraceCollector:
    """Appends trace-worthy workflow events into CIO step-log storage."""

    def __init__(self, workflow_step_service: WorkflowStepLogService):
        self.workflow_step_service = workflow_step_service

    async def append(self, event: Any) -> Any | None:
        if event.kind not in {"trace", "status"}:
            return None
        return await self.workflow_step_service.record_event(event)

    async def summarize(self, trace_id: str) -> dict[str, Any]:
        return await self.workflow_step_service.summarize_trace(trace_id)
