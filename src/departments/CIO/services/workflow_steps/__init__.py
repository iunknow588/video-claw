from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from fastapi.encoders import jsonable_encoder

from departments.CEO.services.control_plane import control_plane
from departments.CIO.models.step_log import WorkflowStepLog
from departments.CIO.services.data_access.workflow_repository import WorkflowRepository


class WorkflowStepLogService:
    """Workflow step service backed by CIO repositories."""

    def __init__(self, session):
        self.repository = WorkflowRepository(session)

    async def record_step(
        self,
        *,
        trace_id: str,
        skill_name: str,
        event_type: str,
        status: str,
        parent_id: str | None = None,
        input_json: dict[str, Any] | None = None,
        output_json: dict[str, Any] | None = None,
        error_message: str | None = None,
        cost: int = 0,
        metadata_json: dict[str, Any] | None = None,
    ) -> WorkflowStepLog:
        return await self.repository.create_step(
            {
                "trace_id": trace_id,
                "parent_id": parent_id,
                "skill_name": skill_name,
                "event_type": event_type,
                "status": status,
                "input_json": jsonable_encoder(input_json or {}),
                "output_json": jsonable_encoder(output_json or {}),
                "error_message": error_message,
                "cost": cost,
                "metadata_json": jsonable_encoder(metadata_json or {}),
            }
        )

    async def record_event(self, event: Any) -> WorkflowStepLog:
        return await self.record_step(
            trace_id=event.trace_id,
            skill_name=event.source,
            event_type=event.event_type,
            status=event.status or "recorded",
            parent_id=event.parent_id,
            input_json=jsonable_encoder(event.input_json or {}),
            output_json=jsonable_encoder(event.output_json or {}),
            error_message=event.error_message,
            cost=int(event.cost or 0),
            metadata_json=jsonable_encoder(event.metadata_json or {}),
        )

    async def list_steps(
        self,
        *,
        limit: int = 200,
        trace_id: str | None = None,
        skill_name: str | None = None,
        event_type: str | None = None,
        ascending: bool = False,
    ) -> list[WorkflowStepLog]:
        return await self.repository.list_steps(
            limit=limit,
            trace_id=trace_id,
            skill_name=skill_name,
            event_type=event_type,
            ascending=ascending,
        )

    async def summarize_trace(self, trace_id: str) -> dict[str, Any]:
        steps = await self.repository.list_steps(limit=5000, trace_id=trace_id, ascending=True)
        status_counts = Counter(step.status for step in steps)
        event_counts = Counter(step.event_type for step in steps)
        skill_counts = Counter(step.skill_name for step in steps)
        token_usage_by_skill: Counter[str] = Counter()
        token_usage_by_lead: Counter[str] = Counter()
        failed_steps = [
            {
                "skill_name": step.skill_name,
                "event_type": step.event_type,
                "status": step.status,
                "error_message": step.error_message,
                "created_at": step.created_at,
            }
            for step in steps
            if step.status == "failed" or step.event_type == "fail"
        ]
        started_at: datetime | None = steps[0].created_at if steps else None
        finished_at: datetime | None = steps[-1].created_at if steps else None
        total_cost = sum(int(step.cost or 0) for step in steps)
        total_tokens = 0
        main_route = control_plane.get_main_route()
        supporting_leaders = [item["name"] for item in control_plane.list_leaders() if item["name"] not in main_route]
        pipeline_order = ["ceo.workflow", *main_route, *supporting_leaders]
        stage_statuses = {
            stage: next(
                (
                    step.status
                    for step in reversed(steps)
                    if step.skill_name == stage or self._skill_to_lead_group(step.skill_name) == stage
                ),
                None,
            )
            for stage in pipeline_order
        }
        for step in steps:
            metadata_json = step.metadata_json or {}
            token_usage = metadata_json.get("token_usage") or {}
            step_tokens = int(token_usage.get("total_tokens", 0) or 0)
            if step_tokens <= 0:
                continue
            total_tokens += step_tokens
            token_usage_by_skill[step.skill_name] += step_tokens
            token_usage_by_lead[self._skill_to_lead_group(step.skill_name)] += step_tokens

        return {
            "trace_id": trace_id,
            "step_count": len(steps),
            "event_counts": dict(event_counts),
            "status_counts": dict(status_counts),
            "skill_counts": dict(skill_counts),
            "pipeline_order": pipeline_order,
            "stage_statuses": stage_statuses,
            "failed_steps": failed_steps,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "token_usage_by_skill": dict(token_usage_by_skill),
            "token_usage_by_lead": dict(token_usage_by_lead),
            "started_at": started_at,
            "finished_at": finished_at,
        }

    def _skill_to_lead_group(self, skill_name: str) -> str:
        if skill_name.startswith("lead.research_development"):
            return "lead.research_development"
        if skill_name.startswith("lead."):
            parts = skill_name.split(".")
            if len(parts) >= 2:
                return ".".join(parts[:2])
        if skill_name.startswith("ceo"):
            return "ceo.workflow"
        if skill_name.startswith("log"):
            return "lead.cio"
        return "other"
