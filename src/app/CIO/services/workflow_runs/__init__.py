from __future__ import annotations

from app.CIO.models.workflow import WorkflowRun
from app.CIO.services.data_access.workflow_repository import WorkflowRepository


class WorkflowRunService:
    """Workflow run service backed by CIO repositories."""

    def __init__(self, session):
        self.repository = WorkflowRepository(session)

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
        return await self.repository.create_run(
            {
                "trace_id": trace_id,
                "workflow_type": workflow_type,
                "domain": domain,
                "platform": platform,
                "status": "pending",
                "audience": audience,
                "publish_goal": publish_goal,
                "content_type": content_type,
                "style": style,
                "video_style": video_style,
                "duration": duration,
                "expanded_queries": expanded_queries,
            }
        )

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
        updates = {
            "status": "completed",
            "selected_hotspot_ids": selected_hotspot_ids,
            "prompt_package": prompt_package,
            "analysis_ids": analysis_ids,
            "script_id": script_id,
            "video_task_id": video_task_id,
            "result_payload": result_payload,
        }
        if expanded_queries is not None:
            updates["expanded_queries"] = expanded_queries
        return await self.repository.update_run(record, updates)

    async def mark_failed(self, record: WorkflowRun, *, error_message: str) -> WorkflowRun:
        return await self.repository.update_run(record, {"status": "failed", "error_message": error_message})

    async def list_runs(
        self,
        *,
        limit: int = 50,
        domain: str | None = None,
        platform: str | None = None,
        status: str | None = None,
    ) -> list[WorkflowRun]:
        return await self.repository.list_runs(limit=limit, domain=domain, platform=platform, status=status)

    async def get_by_uuid(self, workflow_run_id: str) -> WorkflowRun | None:
        return await self.repository.get_run_by_uuid(workflow_run_id)
