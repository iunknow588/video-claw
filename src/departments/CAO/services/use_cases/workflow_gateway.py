from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from departments.CEO.services.orchestration.domain_workflow import DomainWorkflowService
from departments.CEO.skills.registry import ensure_builtin_skills_registered, registry
from departments.CIO.schemas.video import DomainWorkflowRequest
from departments.CIO.services.workflow_runs import WorkflowRunService
from departments.CIO.services.workflow_steps import WorkflowStepLogService


class WorkflowGatewayUseCase:
    """CAO-owned public workflow gateway backed by the internal workflow engine."""

    def __init__(self, session: AsyncSession):
        self.domain_workflow_service = DomainWorkflowService(session)
        self.workflow_run_service = WorkflowRunService(session)
        self.workflow_step_service = WorkflowStepLogService(session)

    async def list_registered_skills(self) -> list[dict[str, Any]]:
        ensure_builtin_skills_registered()
        return registry.list_descriptors()

    async def run_domain_workflow(self, request: DomainWorkflowRequest) -> dict[str, Any]:
        return await self.domain_workflow_service.run(request)

    async def list_workflow_runs(
        self,
        *,
        limit: int,
        domain: str | None,
        platform: str | None,
        status: str | None,
    ) -> list[Any]:
        return await self.workflow_run_service.list_runs(
            limit=limit,
            domain=domain,
            platform=platform,
            status=status,
        )

    async def list_workflow_steps(
        self,
        *,
        limit: int,
        trace_id: str | None,
        skill_name: str | None,
        event_type: str | None,
    ) -> list[Any]:
        return await self.workflow_step_service.list_steps(
            limit=limit,
            trace_id=trace_id,
            skill_name=skill_name,
            event_type=event_type,
        )

    async def get_workflow_trace(self, workflow_run_id: str) -> dict[str, Any]:
        run = await self.workflow_run_service.get_by_uuid(workflow_run_id)
        if not run:
            raise LookupError("Workflow run not found")

        trace_id = getattr(run, "trace_id", None)
        if isinstance(run.result_payload, dict):
            trace_id = trace_id or run.result_payload.get("trace_id")

        steps = await self.workflow_step_service.list_steps(limit=500, trace_id=trace_id) if trace_id else []
        summary = (
            await self.workflow_step_service.summarize_trace(trace_id)
            if trace_id
            else {"trace_id": None, "step_count": 0}
        )
        return {"run": run, "steps": steps, "summary": summary}
