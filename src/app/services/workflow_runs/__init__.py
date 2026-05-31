"""
Workflow run persistence helpers.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.encoders import jsonable_encoder

from app.models.workflow import WorkflowRun


class WorkflowRunService:
    """Handles workflow run record persistence and querying."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_run(
        self,
        *,
        trace_id: str | None,
        workflow_type: str,
        domain: str,
        platform: str,
        audience: str | None,
        publish_goal: str | None,
        content_type: str,
        style: str,
        video_style: str | None,
        duration: int,
        expanded_queries: list[str],
    ) -> WorkflowRun:
        record = WorkflowRun(
            trace_id=trace_id,
            workflow_type=workflow_type,
            domain=domain,
            platform=platform,
            status="pending",
            audience=audience,
            publish_goal=publish_goal,
            content_type=content_type,
            style=style,
            video_style=video_style,
            duration=duration,
            expanded_queries=expanded_queries,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def mark_completed(
        self,
        record: WorkflowRun,
        *,
        expanded_queries: list[str] | None = None,
        selected_hotspot_ids: list[str],
        prompt_package: dict,
        analysis_ids: list[str],
        script_id: str,
        video_task_id: str | None,
        result_payload: dict,
    ) -> WorkflowRun:
        record.status = "completed"
        if expanded_queries is not None:
            record.expanded_queries = jsonable_encoder(expanded_queries)
        record.selected_hotspot_ids = selected_hotspot_ids
        record.prompt_package = jsonable_encoder(prompt_package)
        record.analysis_ids = jsonable_encoder(analysis_ids)
        record.script_id = script_id
        record.video_task_id = video_task_id
        record.result_payload = jsonable_encoder(result_payload)
        await self.session.flush()
        return record

    async def mark_failed(self, record: WorkflowRun, *, error_message: str) -> WorkflowRun:
        record.status = "failed"
        record.error_message = error_message
        await self.session.flush()
        return record

    async def list_runs(
        self,
        *,
        limit: int = 50,
        domain: str | None = None,
        platform: str | None = None,
        status: str | None = None,
    ) -> list[WorkflowRun]:
        query = select(WorkflowRun).order_by(WorkflowRun.created_at.desc()).limit(limit)
        if domain:
            query = query.where(WorkflowRun.domain == domain)
        if platform:
            query = query.where(WorkflowRun.platform == platform)
        if status:
            query = query.where(WorkflowRun.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_uuid(self, workflow_run_id: str) -> WorkflowRun | None:
        result = await self.session.execute(select(WorkflowRun).where(WorkflowRun.uuid == workflow_run_id))
        return result.scalar_one_or_none()
