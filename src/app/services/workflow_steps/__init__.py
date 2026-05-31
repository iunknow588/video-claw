from __future__ import annotations

from collections import Counter
from datetime import datetime
from sqlalchemy import select
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.step_log import WorkflowStepLog
from app.services.ceo_control_plane import control_plane


class WorkflowStepLogService:
    """Persists step-level workflow logs."""

    def __init__(self, session: AsyncSession):
        self.session = session

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
        record = WorkflowStepLog(
            trace_id=trace_id,
            parent_id=parent_id,
            skill_name=skill_name,
            event_type=event_type,
            status=status,
            input_json=jsonable_encoder(input_json or {}),
            output_json=jsonable_encoder(output_json or {}),
            error_message=error_message,
            cost=cost,
            metadata_json=jsonable_encoder(metadata_json or {}),
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def list_steps(
        self,
        *,
        limit: int = 200,
        trace_id: str | None = None,
        skill_name: str | None = None,
        event_type: str | None = None,
    ) -> list[WorkflowStepLog]:
        query = select(WorkflowStepLog).order_by(WorkflowStepLog.created_at.desc()).limit(limit)
        if trace_id:
            query = query.where(WorkflowStepLog.trace_id == trace_id)
        if skill_name:
            query = query.where(WorkflowStepLog.skill_name == skill_name)
        if event_type:
            query = query.where(WorkflowStepLog.event_type == event_type)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def summarize_trace(self, trace_id: str) -> dict[str, Any]:
        query = (
            select(WorkflowStepLog)
            .where(WorkflowStepLog.trace_id == trace_id)
            .order_by(WorkflowStepLog.created_at.asc(), WorkflowStepLog.id.asc())
        )
        result = await self.session.execute(query)
        steps = list(result.scalars().all())
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
        supporting_leaders = [
            item["name"]
            for item in control_plane.list_leaders()
            if item["name"] not in main_route
        ]
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
