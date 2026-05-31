from __future__ import annotations

from datetime import UTC, datetime, timedelta
from statistics import mean
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.leaders.organization import LEADER_STAGE_LABELS_CN
from app.services.ceo_control_plane import control_plane
from app.services.cio import CIOInformationService
from app.services.finance import FinanceService
from app.services.leader_reports import LeaderReportService
from app.services.operations import OperationsService
from app.services.workflow_runs import WorkflowRunService
from app.services.workflow_steps import WorkflowStepLogService
from app.skills.catalog import SKILL_METADATA_OVERRIDES
from app.skills.ceo.workflow_ceo import CEOWorkflowSkill
from app.skills.runtime import SkillRuntimeManager


class CEOControlService:
    """DB-backed CEO control service that enriches the management skill with live metrics."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.operations_service = OperationsService(session)
        self.finance_service = FinanceService(session)
        self.cio_service = CIOInformationService(session)
        self.leader_report_service = LeaderReportService(session)
        self.workflow_run_service = WorkflowRunService(session)
        self.workflow_step_service = WorkflowStepLogService(session)
        self.skill_runtime = SkillRuntimeManager()
        self.ceo_skill = CEOWorkflowSkill()

    async def list_leaders(self) -> dict[str, Any]:
        leaders = (await self._invoke_skill("list_leaders", {}))["leaders"]
        metrics = await self._collect_leader_metrics()
        return {
            "mission": control_plane.mission,
            "scope": control_plane.managed_scope,
            "leaders": [self._merge_leader_metrics(item, metrics.get(item["name"], {})) for item in leaders],
            "count": len(leaders),
        }

    async def get_leader_status(self, leader_name: str) -> dict[str, Any]:
        leader = (await self._invoke_skill("get_leader_status", {"name": leader_name}))["leader"]
        metrics = await self._collect_leader_metrics()
        return {
            "mission": control_plane.mission,
            "scope": control_plane.managed_scope,
            "leader": self._merge_leader_metrics(leader, metrics.get(leader["name"], {})),
        }

    async def add_leader(self, name: str, config: dict[str, Any]) -> dict[str, Any]:
        return await self._invoke_skill("add_leader", {"name": name, "config": config})

    async def remove_leader(self, name: str) -> dict[str, Any]:
        return await self._invoke_skill("remove_leader", {"name": name})

    async def update_leader_config(self, name: str, config: dict[str, Any]) -> dict[str, Any]:
        return await self._invoke_skill("update_leader_config", {"name": name, "config": config})

    async def rollback_leader(self, name: str, version: int) -> dict[str, Any]:
        return await self._invoke_skill("rollback_leader", {"name": name, "version": version})

    async def get_workflow(self) -> dict[str, Any]:
        workflow = (await self._invoke_skill("get_workflow", {}))["workflow"]
        return {
            "mission": control_plane.mission,
            "scope": control_plane.managed_scope,
            "workflow": workflow,
            "route_labels": [self._stage_label(item) for item in workflow.get("main_route", [])],
        }

    async def set_workflow(self, graph_definition: dict[str, Any]) -> dict[str, Any]:
        return await self._invoke_skill("set_workflow", {"graph_definition": graph_definition})

    async def add_edge(self, from_leader: str, to_leader: str) -> dict[str, Any]:
        return await self._invoke_skill(
            "add_edge",
            {"from_leader": from_leader, "to_leader": to_leader},
        )

    async def add_conditional_edge(
        self,
        from_leader: str,
        router_func: str,
        mapping: dict[str, str],
    ) -> dict[str, Any]:
        return await self._invoke_skill(
            "add_conditional_edge",
            {
                "from_leader": from_leader,
                "router_func": router_func,
                "mapping": mapping,
            },
        )

    async def issue_optimize_command(
        self,
        *,
        leader_name: str,
        target_metric: str,
        goal_value: Any,
        note: str | None = None,
    ) -> dict[str, Any]:
        result = await self._invoke_skill(
            "issue_optimize_command",
            {
                "leader_name": leader_name,
                "target_metric": target_metric,
                "goal_value": goal_value,
                "note": note,
            },
        )
        result["leader"] = (await self.get_leader_status(leader_name))["leader"]
        return result

    async def request_leader_report(self, leader_name: str) -> dict[str, Any]:
        result = await self._invoke_skill("request_leader_report", {"leader_name": leader_name})
        company_status = await self.get_company_status()
        report = await self._submit_leader_report(
            leader_name=leader_name,
            report_type="requested",
            cadence="on_demand",
            source="ceo_pull",
            context=company_status,
        )
        result["report"] = report
        return result

    async def approve_leader_change(self, leader_name: str, proposal: dict[str, Any]) -> dict[str, Any]:
        return await self._invoke_skill(
            "approve_leader_change",
            {"leader_name": leader_name, "proposal": proposal},
        )

    async def set_leader_budget(self, leader_name: str, token_limit: int) -> dict[str, Any]:
        return await self._invoke_skill(
            "set_leader_budget",
            {"leader_name": leader_name, "token_limit": token_limit},
        )

    async def adjust_resource_allocation(
        self,
        leader_name: str,
        resource_type: str,
        amount: Any,
    ) -> dict[str, Any]:
        return await self._invoke_skill(
            "adjust_resource_allocation",
            {
                "leader_name": leader_name,
                "resource_type": resource_type,
                "amount": amount,
            },
        )

    async def enable_evolution(self) -> dict[str, Any]:
        return await self._invoke_skill("enable_evolution", {})

    async def disable_evolution(self) -> dict[str, Any]:
        return await self._invoke_skill("disable_evolution", {})

    async def evolution_cycle(self) -> dict[str, Any]:
        company_status = await self.get_company_status()
        result = await self._invoke_skill("evolution_cycle", {"company_status": company_status})
        periodic_reports = await self.collect_periodic_reports(company_status=company_status, cadence="daily")
        return {
            **result,
            "company_status": company_status,
            "periodic_reports": periodic_reports["reports"],
        }

    async def get_company_status(self) -> dict[str, Any]:
        operations_summary = await self.operations_service.build_summary()
        finance_metrics = await self.finance_service.build_summary()
        information_metrics = await self.cio_service.build_summary()
        runs = await self.workflow_run_service.list_runs(limit=200)
        leader_metrics = await self._collect_leader_metrics(runs)
        run_summaries = await self._collect_trace_summaries(runs)

        total_runs = len(runs)
        completed_runs = sum(1 for run in runs if run.status == "completed")
        failed_runs = sum(1 for run in runs if run.status == "failed")
        success_rate = round(completed_runs / total_runs, 4) if total_runs else 0.0
        qa_runs = [run for run in runs if isinstance(run.result_payload, dict) and run.result_payload.get("qa_status")]
        qa_passed = sum(
            1
            for run in qa_runs
            if isinstance(run.result_payload, dict) and run.result_payload.get("qa_status") == "passed"
        )
        qa_pass_rate = round(qa_passed / len(qa_runs), 4) if qa_runs else 0.0
        render_runs = [
            run for run in runs
            if isinstance(run.result_payload, dict)
            and isinstance((run.result_payload.get("production_bundle") or {}), dict)
            and isinstance(((run.result_payload.get("production_bundle") or {}).get("render_bundle") or {}), dict)
        ]
        ffmpeg_preview_runs = 0
        passthrough_runs = 0
        placeholder_runs = 0
        rendered_with_delivery_url = 0
        for run in render_runs:
            render_bundle = ((run.result_payload or {}).get("production_bundle") or {}).get("render_bundle") or {}
            render_mode = str(render_bundle.get("render_mode") or "")
            if render_mode == "ffmpeg_preview":
                ffmpeg_preview_runs += 1
            elif render_mode == "passthrough_video_task":
                passthrough_runs += 1
            elif render_mode == "preview_placeholder":
                placeholder_runs += 1
            if render_bundle.get("delivery_asset_url"):
                rendered_with_delivery_url += 1
        render_success_rate = round(rendered_with_delivery_url / len(render_runs), 4) if render_runs else 0.0
        avg_duration_ms = round(
            mean([item["duration_ms"] for item in run_summaries if item["duration_ms"] is not None]),
            2,
        ) if run_summaries else 0.0
        avg_tokens = round(
            mean([item["total_tokens"] for item in run_summaries if item["total_tokens"] > 0]),
            2,
        ) if run_summaries else 0.0

        leader_statuses = []
        for item in control_plane.list_leaders():
            leader_statuses.append(self._merge_leader_metrics(item, leader_metrics.get(item["name"], {})))
        leader_statuses.sort(key=lambda item: item["name"])

        weakest_leader = None
        weakest_score = 2.0
        for item in leader_statuses:
            success = float(item.get("metrics", {}).get("success_rate") or 0.0)
            if item.get("metrics", {}).get("run_count", 0) and success < weakest_score:
                weakest_score = success
                weakest_leader = item["name"]

        status_payload = {
            "mission": control_plane.mission,
            "scope": control_plane.managed_scope,
            "workflow": control_plane.get_workflow(),
            "workflow_leaders": control_plane.get_main_route(),
            "run_metrics": {
                "total_runs": total_runs,
                "completed_runs": completed_runs,
                "failed_runs": failed_runs,
                "success_rate": success_rate,
                "avg_duration_ms": avg_duration_ms,
                "avg_tokens": avg_tokens,
            },
            "quality_metrics": {
                "qa_checked_runs": len(qa_runs),
                "qa_passed_runs": qa_passed,
                "qa_pass_rate": qa_pass_rate,
            },
            "render_metrics": {
                "render_checked_runs": len(render_runs),
                "delivery_asset_ready_runs": rendered_with_delivery_url,
                "render_success_rate": render_success_rate,
                "ffmpeg_preview_runs": ffmpeg_preview_runs,
                "passthrough_video_task_runs": passthrough_runs,
                "preview_placeholder_runs": placeholder_runs,
            },
            "operations_summary": operations_summary,
            "finance_metrics": finance_metrics,
            "information_metrics": information_metrics,
            "leader_statuses": leader_statuses,
            "active_leader_count": len(leader_statuses),
            "pending_optimize_commands": len(
                [item for item in control_plane.optimize_commands if item.get("status") == "issued"]
            ),
            "pending_report_requests": len(
                [item for item in control_plane.report_requests if item.get("status") == "requested"]
            ),
            "evolution_enabled": control_plane.evolution_enabled,
            "weakest_leader": weakest_leader,
            "non_workflow_leaders": control_plane.get_non_workflow_leaders(),
            "org_title_registry": control_plane.get_title_registry(),
            "out_of_scope_departments": [],
            "governance_note": (
                "Promotion and CHO both report to CEO as support departments; Promotion handles user communication, while CHO manages shared agents outside the production main route."
            ),
        }
        report_center = await self._ensure_recent_periodic_reports(status_payload)
        status_payload["report_center"] = report_center
        return status_payload

    async def get_task_progress(self, workflow_run_id: str) -> dict[str, Any]:
        run = await self.workflow_run_service.get_by_uuid(workflow_run_id)
        if not run:
            raise ValueError(f"Workflow run {workflow_run_id} not found")
        summary = await self.workflow_step_service.summarize_trace(run.trace_id) if run.trace_id else {"trace_id": None}
        completed_stages = [
            stage for stage, status in (summary.get("stage_statuses") or {}).items()
            if status in {"success", "completed"}
        ]
        current_stage = self._resolve_current_stage(summary.get("stage_statuses") or {})
        route = control_plane.get_main_route()
        progress_ratio = round(len(completed_stages) / len(route), 4) if route else 0.0
        task_progress = {
            "task_id": run.uuid,
            "trace_id": run.trace_id,
            "status": run.status,
            "domain": run.domain,
            "platform": run.platform,
            "current_stage": current_stage,
            "current_stage_label": self._stage_label(current_stage) if current_stage else None,
            "progress_ratio": progress_ratio,
            "stage_statuses": summary.get("stage_statuses") or {},
            "workflow_route": route,
            "qa_status": (run.result_payload or {}).get("qa_status") if isinstance(run.result_payload, dict) else None,
            "summary": summary,
        }
        result = await self._invoke_skill("get_task_progress", {"task_progress": task_progress})
        return result["task_progress"]

    async def collect_periodic_reports(
        self,
        *,
        company_status: dict[str, Any] | None = None,
        cadence: str = "daily",
    ) -> dict[str, Any]:
        snapshot = company_status or await self.get_company_status()
        reports = []
        for leader in control_plane.list_leaders():
            reports.append(
                await self._submit_leader_report(
                    leader_name=leader["name"],
                    report_type="periodic",
                    cadence=cadence,
                    source="leader",
                    context=snapshot,
                )
            )
        return {"reports": reports, "count": len(reports), "cadence": cadence}

    async def list_leader_reports(
        self,
        *,
        leader_name: str | None = None,
        report_type: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        reports = await self.leader_report_service.list_reports(
            leader_name=leader_name,
            report_type=report_type,
            limit=limit,
        )
        return {
            "reports": [self.leader_report_service.serialize_report(item) for item in reports],
            "count": len(reports),
        }

    async def get_latest_leader_report(
        self,
        *,
        leader_name: str,
        report_type: str | None = None,
    ) -> dict[str, Any]:
        report = await self.leader_report_service.get_latest_report(leader_name=leader_name, report_type=report_type)
        if not report:
            raise ValueError(f"No report found for leader {leader_name}")
        return {"report": self.leader_report_service.serialize_report(report)}

    async def _invoke_skill(self, method_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        invocation = await self.skill_runtime.invoke(
            self.ceo_skill,
            payload,
            descriptor_overrides=SKILL_METADATA_OVERRIDES.get(self.ceo_skill.skill_name, {}),
            method_name=method_name,
        )
        return invocation.output_json

    async def _collect_leader_metrics(
        self,
        runs: list[Any] | None = None,
    ) -> dict[str, dict[str, Any]]:
        workflow_runs = runs if runs is not None else await self.workflow_run_service.list_runs(limit=200)
        trace_summaries = await self._collect_trace_summaries(workflow_runs)
        metrics = {
            leader_name: {
                "run_count": 0,
                "success_count": 0,
                "failed_count": 0,
                "success_rate": 0.0,
                "avg_tokens": 0.0,
                "last_status": "never_run",
            }
            for leader_name in [item["name"] for item in control_plane.list_leaders()]
        }
        token_buckets: dict[str, list[int]] = {leader: [] for leader in metrics}
        latest_by_leader: dict[str, tuple[datetime, str]] = {}

        for item in trace_summaries:
            stage_statuses = item["summary"].get("stage_statuses") or {}
            token_usage = item["summary"].get("token_usage_by_lead") or {}
            finished_at = item["summary"].get("finished_at") or item["summary"].get("started_at")
            for leader_name in metrics:
                status = stage_statuses.get(leader_name)
                if status:
                    metrics[leader_name]["run_count"] += 1
                    if status in {"success", "completed"}:
                        metrics[leader_name]["success_count"] += 1
                    if status == "failed":
                        metrics[leader_name]["failed_count"] += 1
                    if finished_at and (leader_name not in latest_by_leader or finished_at > latest_by_leader[leader_name][0]):
                        latest_by_leader[leader_name] = (finished_at, status)
                lead_group = self._skill_group_for_stage(leader_name)
                tokens = int(token_usage.get(lead_group, 0) or 0)
                if tokens > 0:
                    token_buckets[leader_name].append(tokens)

        for leader_name, bucket in metrics.items():
            run_count = bucket["run_count"]
            bucket["success_rate"] = round(bucket["success_count"] / run_count, 4) if run_count else 0.0
            bucket["avg_tokens"] = round(mean(token_buckets[leader_name]), 2) if token_buckets[leader_name] else 0.0
            if leader_name in latest_by_leader:
                bucket["last_status"] = latest_by_leader[leader_name][1]
        return metrics

    async def _collect_trace_summaries(self, runs: list[Any]) -> list[dict[str, Any]]:
        summaries = []
        for run in runs:
            if not getattr(run, "trace_id", None):
                continue
            summary = await self.workflow_step_service.summarize_trace(run.trace_id)
            summaries.append(
                {
                    "run_id": run.uuid,
                    "summary": summary,
                    "duration_ms": self._duration_ms(summary.get("started_at"), summary.get("finished_at")),
                    "total_tokens": int(summary.get("total_tokens") or 0),
                }
            )
        return summaries

    async def _submit_leader_report(
        self,
        *,
        leader_name: str,
        report_type: str,
        cadence: str,
        source: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        leader_state = control_plane.get_leader_status(name=leader_name)
        leader_context = {
            **context,
            "leader_status": leader_state,
        }
        report_payload = control_plane.build_leader_periodic_report(name=leader_name, context=leader_context)
        record = await self.leader_report_service.create_report(
            leader_name=leader_name,
            report_type=report_type,
            cadence=cadence,
            source=source,
            report_payload=report_payload,
        )
        return self.leader_report_service.serialize_report(record)

    async def _ensure_recent_periodic_reports(
        self,
        company_status: dict[str, Any],
        *,
        max_age_minutes: int = 30,
    ) -> dict[str, Any]:
        threshold = datetime.now(UTC) - timedelta(minutes=max_age_minutes)
        latest_reports: list[dict[str, Any]] = []
        stale_leaders: list[str] = []
        for leader in control_plane.list_leaders():
            leader_name = leader["name"]
            latest = await self.leader_report_service.get_latest_report(leader_name=leader_name, report_type="periodic")
            if latest is None or (latest.created_at and latest.created_at.replace(tzinfo=UTC) < threshold):
                stale_leaders.append(leader_name)
                serialized = await self._submit_leader_report(
                    leader_name=leader_name,
                    report_type="periodic",
                    cadence="auto",
                    source="leader",
                    context=company_status,
                )
                latest_reports.append(serialized)
            else:
                latest_reports.append(self.leader_report_service.serialize_report(latest))
        latest_reports.sort(key=lambda item: (item.get("created_at") or datetime.min), reverse=True)
        return {
            "latest_reports": latest_reports,
            "stale_leaders_refreshed": stale_leaders,
            "auto_refresh_window_minutes": max_age_minutes,
        }

    def _merge_leader_metrics(self, leader: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
        merged = dict(leader)
        merged["metrics"] = {
            "run_count": int(metrics.get("run_count", 0) or 0),
            "success_count": int(metrics.get("success_count", 0) or 0),
            "failed_count": int(metrics.get("failed_count", 0) or 0),
            "success_rate": float(metrics.get("success_rate", 0.0) or 0.0),
            "avg_tokens": float(metrics.get("avg_tokens", 0.0) or 0.0),
            "last_status": metrics.get("last_status", "never_run"),
        }
        return merged

    def _resolve_current_stage(self, stage_statuses: dict[str, str]) -> str | None:
        route = control_plane.get_main_route()
        running = next((stage for stage in route if stage_statuses.get(stage) == "running"), None)
        if running:
            return running
        for stage in reversed(route):
            if stage_statuses.get(stage):
                return stage
        return None

    def _stage_label(self, stage_name: str | None) -> str:
        return LEADER_STAGE_LABELS_CN.get(stage_name or "", stage_name or "未知阶段")

    def _skill_group_for_stage(self, stage_name: str) -> str:
        if stage_name == "lead.promotion":
            return "other"
        if stage_name.startswith("lead."):
            return stage_name
        return stage_name.split(".")[0]

    def _duration_ms(self, started_at: Any, finished_at: Any) -> float | None:
        if not isinstance(started_at, datetime) or not isinstance(finished_at, datetime):
            return None
        return max((finished_at - started_at).total_seconds() * 1000, 0.0)
