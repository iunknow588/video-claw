from __future__ import annotations

from statistics import mean
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from departments.CEO.services.control_plane import control_plane
from departments.CIO.services.workflow_runs import WorkflowRunService
from departments.CIO.services.workflow_steps import WorkflowStepLogService


PUBLIC_STAGE_LABELS = {
    "lead.cfo": "财务闸门",
    "lead.research": "调研",
    "lead.analysis": "分析",
    "lead.research_development": "技术策划",
    "lead.production": "生产",
    "lead.qa": "质检",
    "lead.publish": "对外交付",
}


class CAOConsoleService:
    """CAO-facing public console service.

    The CEO control plane remains internal. This service exposes only
    pipeline-oriented status, delivery progress, and run history.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.workflow_run_service = WorkflowRunService(session)
        self.workflow_step_service = WorkflowStepLogService(session)

    async def get_pipeline_status(self, *, limit: int = 8) -> dict[str, Any]:
        runs = await self.workflow_run_service.list_runs(limit=200)
        recent_runs = await self.workflow_run_service.list_runs(limit=limit)

        total_runs = len(runs)
        completed_runs = sum(1 for run in runs if run.status == "completed")
        failed_runs = sum(1 for run in runs if run.status == "failed")
        active_runs = max(total_runs - completed_runs - failed_runs, 0)
        success_rate = round(completed_runs / total_runs, 4) if total_runs else 0.0

        qa_runs = [
            run
            for run in runs
            if isinstance(run.result_payload, dict) and run.result_payload.get("qa_status")
        ]
        qa_passed = sum(
            1
            for run in qa_runs
            if isinstance(run.result_payload, dict) and run.result_payload.get("qa_status") == "passed"
        )
        qa_pass_rate = round(qa_passed / len(qa_runs), 4) if qa_runs else 0.0

        delivery_ready_runs = sum(
            1
            for run in runs
            if isinstance(run.result_payload, dict) and run.result_payload.get("video_url")
        )
        delivery_ready_rate = round(delivery_ready_runs / total_runs, 4) if total_runs else 0.0

        trace_summaries = []
        for run in runs[:20]:
            if getattr(run, "trace_id", None):
                trace_summaries.append(await self.workflow_step_service.summarize_trace(run.trace_id))
        duration_samples = [
            summary["finished_at"].timestamp() * 1000 - summary["started_at"].timestamp() * 1000
            for summary in trace_summaries
            if summary.get("started_at") and summary.get("finished_at")
        ]
        token_samples = [
            summary["total_tokens"]
            for summary in trace_summaries
            if summary.get("total_tokens", 0) > 0
        ]
        avg_duration_ms = round(mean(duration_samples), 2) if duration_samples else 0.0
        avg_tokens = round(mean(token_samples), 2) if token_samples else 0.0

        latest_run = recent_runs[0] if recent_runs else None
        latest_summary = (
            await self.workflow_step_service.summarize_trace(latest_run.trace_id)
            if latest_run and getattr(latest_run, "trace_id", None)
            else {"stage_statuses": {}}
        )

        route = control_plane.get_main_route()
        stage_statuses = [
            {
                "name": stage_name,
                "label": PUBLIC_STAGE_LABELS.get(stage_name, stage_name),
                "status": (latest_summary.get("stage_statuses") or {}).get(stage_name) or "idle",
            }
            for stage_name in route
        ]

        return {
            "console_title": "流程交付台 / CAO 管理台",
            "console_subtitle": "CEO 隐身运行，CAO 仅对外展示生产链路、交付进度与结果。",
            "display_policy": {
                "ceo_visible": False,
                "workflow_visible": True,
                "delivery_visible": True,
            },
            "pipeline_metrics": {
                "total_runs": total_runs,
                "completed_runs": completed_runs,
                "failed_runs": failed_runs,
                "active_runs": active_runs,
                "success_rate": success_rate,
                "qa_pass_rate": qa_pass_rate,
                "delivery_ready_rate": delivery_ready_rate,
                "avg_duration_ms": avg_duration_ms,
                "avg_tokens": avg_tokens,
            },
            "stage_statuses": stage_statuses,
            "recent_runs": [self._serialize_public_run(run) for run in recent_runs],
        }

    async def list_public_runs(
        self,
        *,
        limit: int = 8,
        domain: str | None = None,
        platform: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        runs = await self.workflow_run_service.list_runs(
            limit=limit,
            domain=domain,
            platform=platform,
            status=status,
        )
        return [self._serialize_public_run(run) for run in runs]

    async def get_public_trace(self, workflow_run_id: str) -> dict[str, Any]:
        run = await self.workflow_run_service.get_by_uuid(workflow_run_id)
        if not run:
            raise ValueError(f"Workflow run {workflow_run_id} not found")

        trace_id = getattr(run, "trace_id", None)
        if isinstance(run.result_payload, dict):
            trace_id = trace_id or run.result_payload.get("trace_id")

        steps = await self.workflow_step_service.list_steps(limit=500, trace_id=trace_id) if trace_id else []
        summary = await self.workflow_step_service.summarize_trace(trace_id) if trace_id else {"trace_id": None, "step_count": 0}

        public_stage_statuses = [
            {
                "name": stage_name,
                "label": PUBLIC_STAGE_LABELS.get(stage_name, stage_name),
                "status": (summary.get("stage_statuses") or {}).get(stage_name) or "idle",
            }
            for stage_name in control_plane.get_main_route()
        ]

        public_steps = []
        for step in steps:
            stage_name = self._to_stage_name(step.skill_name)
            if stage_name not in PUBLIC_STAGE_LABELS:
                continue
            public_steps.append(
                {
                    "stage": stage_name,
                    "stage_label": PUBLIC_STAGE_LABELS.get(stage_name, stage_name),
                    "skill_name": step.skill_name,
                    "event_type": step.event_type,
                    "status": step.status,
                    "created_at": step.created_at,
                    "message": self._extract_step_message(step),
                }
            )

        return {
            "run": self._serialize_public_run(run),
            "summary": {
                "trace_id": summary.get("trace_id"),
                "step_count": summary.get("step_count", 0),
                "total_cost": summary.get("total_cost", 0),
                "total_tokens": summary.get("total_tokens", 0),
                "stage_statuses": {
                    item["name"]: item["status"] for item in public_stage_statuses
                },
                "pipeline_order": [item["name"] for item in public_stage_statuses],
            },
            "public_stage_statuses": public_stage_statuses,
            "public_steps": public_steps,
        }

    def _serialize_public_run(self, run: Any) -> dict[str, Any]:
        result_payload = run.result_payload if isinstance(run.result_payload, dict) else {}
        return {
            "uuid": run.uuid,
            "domain": run.domain,
            "platform": run.platform,
            "status": run.status,
            "duration": run.duration,
            "created_at": run.created_at,
            "trace_id": getattr(run, "trace_id", None),
            "qa_status": result_payload.get("qa_status"),
            "video_url": result_payload.get("video_url"),
            "video_task_id": result_payload.get("video_task_id"),
            "publish_goal": getattr(run, "publish_goal", None),
        }

    def _to_stage_name(self, skill_name: str) -> str:
        if skill_name.startswith("lead.research_development"):
            return "lead.research_development"
        if skill_name.startswith("lead."):
            parts = skill_name.split(".")
            if len(parts) >= 2:
                return ".".join(parts[:2])
        return "other"

    def _extract_step_message(self, step: Any) -> str | None:
        output_json = step.output_json if isinstance(step.output_json, dict) else {}
        metadata_json = step.metadata_json if isinstance(step.metadata_json, dict) else {}
        for key in ("message", "summary", "note"):
            if output_json.get(key):
                return str(output_json[key])
            if metadata_json.get(key):
                return str(metadata_json[key])
        if step.error_message:
            return str(step.error_message)
        return None
