from __future__ import annotations

from datetime import datetime
from statistics import mean
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from departments.CEO.services.control_plane import control_plane
from departments.CIO.services.system_settings import DEFAULT_IDENTITY_NAMES, SystemSettingsService
from departments.CIO.services.workflow_runs import WorkflowRunService
from departments.CIO.services.workflow_steps import WorkflowStepLogService
from departments.CMO.services.public_progress import (
    PUBLIC_STAGE_LABELS,
    STAGE_IDENTITY_KEYS,
    build_public_status_payload,
)

PUBLIC_WORKFLOW_TYPE_LABELS = {
    "domain_auto_run": "自动制作流程",
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
        self.system_settings_service = SystemSettingsService(session)

    async def get_pipeline_status(self, *, limit: int = 8) -> dict[str, Any]:
        identity_settings = await self.system_settings_service.get_identity_settings()
        names = identity_settings["names"]
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
            "console_title": "龙虾宝宝视频制作平台",
            "console_subtitle": f"{names['ceo']} 正在默默关注视频制作流程。",
            "console_frontdesk_name": names["cao"],
            "identity_settings": identity_settings,
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

        identity_settings = await self.system_settings_service.get_identity_settings()
        names = identity_settings["names"]
        trace_id = getattr(run, "trace_id", None)
        result_payload = run.result_payload if isinstance(run.result_payload, dict) else {}
        trace_id = trace_id or result_payload.get("trace_id")

        steps = (
            await self.workflow_step_service.list_steps(limit=500, trace_id=trace_id, ascending=True)
            if trace_id
            else []
        )
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
            actor_key = STAGE_IDENTITY_KEYS.get(stage_name)
            public_steps.append(
                {
                    "stage": stage_name,
                    "stage_label": PUBLIC_STAGE_LABELS.get(stage_name, stage_name),
                    "actor_key": actor_key,
                    "actor_name": names.get(actor_key, DEFAULT_IDENTITY_NAMES.get(actor_key or "", stage_name)),
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
            "identity_settings": identity_settings,
            "public_stage_statuses": public_stage_statuses,
            "public_steps": public_steps,
            "public_artifacts": self._build_public_artifacts(result_payload),
            "public_logs": self._build_public_logs(
                run=run,
                public_steps=public_steps,
                public_artifacts=self._build_public_artifacts(result_payload),
                identity_names=names,
            ),
        }

    async def get_identity_settings(self) -> dict[str, Any]:
        return await self.system_settings_service.get_identity_settings()

    async def update_identity_settings(self, names: dict[str, Any]) -> dict[str, Any]:
        return await self.system_settings_service.update_identity_settings(names)

    def _serialize_public_run(self, run: Any) -> dict[str, Any]:
        result_payload = run.result_payload if isinstance(run.result_payload, dict) else {}
        return {
            "uuid": run.uuid,
            "domain": run.domain,
            "display_domain": self._resolve_public_domain(run, result_payload),
            "platform": run.platform,
            "status": run.status,
            "workflow_type": getattr(run, "workflow_type", None),
            "workflow_type_label": self._label_workflow_type(getattr(run, "workflow_type", None)),
            "duration": run.duration,
            "created_at": run.created_at,
            "trace_id": getattr(run, "trace_id", None),
            "qa_status": result_payload.get("qa_status"),
            "video_url": result_payload.get("video_url"),
            "video_task_id": result_payload.get("video_task_id"),
            "publish_goal": getattr(run, "publish_goal", None),
        }

    def _resolve_public_domain(self, run: Any, result_payload: dict[str, Any]) -> str:
        prompt_package = result_payload.get("prompt_package") if isinstance(result_payload, dict) else {}
        selected_hotspots = result_payload.get("selected_hotspots") if isinstance(result_payload, dict) else None
        candidates = [
            getattr(run, "domain", None),
            getattr(run, "publish_goal", None),
            result_payload.get("domain"),
            prompt_package.get("script_topic") if isinstance(prompt_package, dict) else None,
        ]
        if isinstance(selected_hotspots, list):
            for item in selected_hotspots:
                if isinstance(item, dict):
                    candidates.append(item.get("title"))

        for candidate in candidates:
            normalized = self._normalize_public_text(candidate)
            if normalized:
                return normalized

        platform_label = self._label_platform(getattr(run, "platform", None))
        created_at = getattr(run, "created_at", None)
        if isinstance(created_at, datetime):
            return f"{platform_label}任务 {created_at.strftime('%m-%d %H:%M')}"
        return f"{platform_label}任务"

    @staticmethod
    def _normalize_public_text(value: Any) -> str | None:
        return CAOConsoleService._normalize_public_text_with_limit(value, limit=80)

    @staticmethod
    def _normalize_public_text_with_limit(value: Any, *, limit: int) -> str | None:
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None

        invalid_chars = {"?", "？", "�"}
        meaningful_chars = [char for char in text if not char.isspace()]
        if meaningful_chars and all(char in invalid_chars for char in meaningful_chars):
            return None
        if "????" in text or "？？？？" in text:
            return None

        return text[:limit]

    @staticmethod
    def _label_workflow_type(workflow_type: str | None) -> str:
        normalized = str(workflow_type or "").strip()
        if not normalized:
            return "自动制作流程"
        return PUBLIC_WORKFLOW_TYPE_LABELS.get(normalized, normalized)

    @staticmethod
    def _label_platform(platform: str | None) -> str:
        mapping = {
            "douyin": "抖音",
            "xiaohongshu": "小红书",
            "xigua": "西瓜",
            "bilibili": "B站",
        }
        normalized = str(platform or "").strip().lower()
        return mapping.get(normalized, normalized or "内容")

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

    def _build_public_artifacts(self, result_payload: dict[str, Any]) -> dict[str, Any]:
        research_bundle = result_payload.get("research_bundle") if isinstance(result_payload.get("research_bundle"), dict) else {}
        analysis_bundle = result_payload.get("analysis_bundle") if isinstance(result_payload.get("analysis_bundle"), dict) else {}
        prompt_package = result_payload.get("prompt_package") if isinstance(result_payload.get("prompt_package"), dict) else {}
        production_bundle = result_payload.get("production_bundle") if isinstance(result_payload.get("production_bundle"), dict) else {}
        qa_bundle = result_payload.get("qa_bundle") if isinstance(result_payload.get("qa_bundle"), dict) else {}

        public_artifacts: dict[str, Any] = {}

        research_artifact: dict[str, Any] = {}
        expanded_queries = self._normalize_public_list(
            research_bundle.get("expanded_queries") or result_payload.get("expanded_queries"),
            limit=6,
            max_length=48,
        )
        if expanded_queries:
            research_artifact["expanded_queries"] = expanded_queries

        hotspot_items = research_bundle.get("selected_hotspots") or result_payload.get("selected_hotspots")
        if isinstance(hotspot_items, list):
            serialized_hotspots = [
                serialized
                for item in hotspot_items[:6]
                if (serialized := self._serialize_public_hotspot(item)) is not None
            ]
            if serialized_hotspots:
                research_artifact["selected_hotspots"] = serialized_hotspots

        if research_artifact:
            public_artifacts["research"] = research_artifact

        analysis_reports = analysis_bundle.get("analysis_reports")
        if isinstance(analysis_reports, list):
            serialized_reports = [
                serialized
                for item in analysis_reports[:4]
                if (serialized := self._serialize_public_analysis_report(item)) is not None
            ]
            if serialized_reports:
                public_artifacts["analysis"] = {
                    "report_count": len(serialized_reports),
                    "reports": serialized_reports,
                }

        planning_artifact = self._serialize_public_prompt_package(prompt_package)
        if planning_artifact:
            public_artifacts["planning"] = planning_artifact

        production_artifact = self._serialize_public_script_bundle(production_bundle)
        if production_artifact:
            public_artifacts["production"] = production_artifact

        qa_artifact = self._serialize_public_qa_bundle(qa_bundle)
        if qa_artifact:
            public_artifacts["qa"] = qa_artifact

        return public_artifacts

    def _serialize_public_hotspot(self, item: Any) -> dict[str, Any] | None:
        if not isinstance(item, dict):
            return None

        payload: dict[str, Any] = {}
        for field in ("title", "author", "category"):
            value = self._normalize_public_text_with_limit(item.get(field), limit=64)
            if value:
                payload[field] = value

        for field in ("view_count", "like_count", "comment_count", "share_count", "heat_score"):
            value = item.get(field)
            if isinstance(value, (int, float)):
                payload[field] = value

        url = self._normalize_public_text_with_limit(item.get("url"), limit=240)
        if url:
            payload["url"] = url

        return payload or None

    def _serialize_public_analysis_report(self, item: Any) -> dict[str, Any] | None:
        if not isinstance(item, dict):
            return None

        payload: dict[str, Any] = {}
        report_title = self._normalize_public_text_with_limit(item.get("report_title"), limit=64) or "爆款DNA报告"
        payload["report_title"] = report_title

        for field in ("framework_summary",):
            value = self._normalize_public_text_with_limit(item.get(field), limit=200)
            if value:
                payload[field] = value

        for field in ("hook_design", "emotion_curve"):
            value = self._summarize_public_value(item.get(field))
            if value:
                payload[field] = value

        reusable_elements = self._normalize_public_list(item.get("reusable_elements"), limit=6, max_length=32)
        if reusable_elements:
            payload["reusable_elements"] = reusable_elements

        risk_warnings = self._normalize_public_list(item.get("risk_warnings"), limit=4, max_length=48)
        if risk_warnings:
            payload["risk_warnings"] = risk_warnings

        return payload or None

    def _serialize_public_prompt_package(self, item: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {}

        for field in ("prompt_summary", "script_topic", "video_prompt"):
            limit = 240 if field == "video_prompt" else 180
            value = self._normalize_public_text_with_limit(item.get(field), limit=limit)
            if value:
                payload[field] = value

        for field in ("core_keywords", "hook_keywords", "visual_keywords", "title_candidates", "script_topic_variants"):
            values = self._normalize_public_list(item.get(field), limit=6, max_length=40)
            if values:
                payload[field] = values

        for field in ("video_prompt_variants", "image_prompt_variants"):
            values = self._normalize_public_list(item.get(field), limit=3, max_length=180)
            if values:
                payload[field] = values

        return payload

    def _serialize_public_script_bundle(self, item: dict[str, Any]) -> dict[str, Any]:
        script = item.get("script")
        if not isinstance(script, dict):
            return {}

        payload: dict[str, Any] = {}
        for field in ("title", "topic", "hook", "cta"):
            value = self._normalize_public_text_with_limit(script.get(field), limit=180)
            if value:
                payload[field] = value

        tags = self._normalize_public_list(script.get("tags"), limit=8, max_length=24)
        if tags:
            payload["tags"] = tags

        scenes = script.get("scenes")
        if isinstance(scenes, list):
            public_scenes = [
                serialized
                for scene in scenes[:6]
                if (serialized := self._serialize_public_scene(scene)) is not None
            ]
            if public_scenes:
                payload["scenes"] = public_scenes

        return payload

    def _serialize_public_scene(self, scene: Any) -> dict[str, Any] | None:
        if not isinstance(scene, dict):
            return None

        payload: dict[str, Any] = {}
        field_aliases = {
            "timing": ("timing", "time"),
            "visuals": ("visuals", "shot"),
            "audio": ("audio", "voiceover"),
            "text": ("text", "caption"),
        }
        for public_field, aliases in field_aliases.items():
            for alias in aliases:
                if alias in {"time", "timing"}:
                    value = self._normalize_public_text_with_limit(scene.get(alias), limit=48)
                else:
                    value = self._normalize_public_text_with_limit(scene.get(alias), limit=160)
                if value:
                    payload[public_field] = value
                    break

        return payload or None

    def _serialize_public_qa_bundle(self, item: dict[str, Any]) -> dict[str, Any]:
        qa_report = item.get("qa_report") if isinstance(item.get("qa_report"), dict) else {}
        payload: dict[str, Any] = {}

        if isinstance(qa_report.get("pass"), bool):
            payload["pass"] = qa_report["pass"]
        if isinstance(qa_report.get("overall_score"), (int, float)):
            payload["overall_score"] = qa_report["overall_score"]

        recommendation = self._normalize_public_text_with_limit(qa_report.get("recommendation"), limit=200)
        if recommendation:
            payload["recommendation"] = recommendation

        issues = self._normalize_public_list(qa_report.get("issues"), limit=5, max_length=72)
        if issues:
            payload["issues"] = issues

        return payload

    def _normalize_public_list(self, value: Any, *, limit: int, max_length: int) -> list[str]:
        if not isinstance(value, list):
            return []

        items: list[str] = []
        for entry in value:
            normalized = self._summarize_public_value(entry, max_length=max_length)
            if normalized:
                items.append(normalized[:max_length])
            if len(items) >= limit:
                break
        return items

    def _summarize_public_value(self, value: Any, *, max_length: int = 160) -> str | None:
        if isinstance(value, str):
            normalized = self._normalize_public_text_with_limit(value, limit=max_length)
            if normalized:
                return normalized[:max_length]
            return None

        if isinstance(value, (int, float, bool)):
            return str(value)

        if isinstance(value, list):
            parts: list[str] = []
            for item in value[:4]:
                summarized = self._summarize_public_value(item, max_length=max_length // 2 if max_length > 24 else max_length)
                if summarized:
                    parts.append(summarized)
            if parts:
                return " / ".join(parts)[:max_length]
            return None

        if isinstance(value, dict):
            parts: list[str] = []
            for key, item in list(value.items())[:4]:
                summarized = self._summarize_public_value(item, max_length=max(16, max_length // 3))
                if summarized:
                    parts.append(f"{key}: {summarized}")
            if parts:
                return "；".join(parts)[:max_length]

        return None

    def _build_public_logs(
        self,
        *,
        run: Any,
        public_steps: list[dict[str, Any]],
        public_artifacts: dict[str, Any],
        identity_names: dict[str, str],
    ) -> list[dict[str, Any]]:
        stage_timestamps: dict[str, Any] = {}
        for step in public_steps:
            stage_timestamps[step["stage"]] = step.get("created_at") or stage_timestamps.get(step["stage"])

        logs = self._build_stage_progress_logs(public_steps)

        artifact_builders = [
            ("lead.research", self._build_research_log_entry(public_artifacts.get("research") or {}, identity_names, stage_timestamps.get("lead.research"))),
            ("lead.analysis", self._build_analysis_log_entry(public_artifacts.get("analysis") or {}, identity_names, stage_timestamps.get("lead.analysis"))),
            ("lead.research_development", self._build_planning_log_entry(public_artifacts.get("planning") or {}, identity_names, stage_timestamps.get("lead.research_development"))),
            ("lead.production", self._build_production_log_entry(public_artifacts.get("production") or {}, identity_names, stage_timestamps.get("lead.production"))),
            ("lead.qa", self._build_qa_log_entry(public_artifacts.get("qa") or {}, identity_names, stage_timestamps.get("lead.qa"))),
        ]
        for _, entry in artifact_builders:
            if entry:
                logs.append(entry)

        failure_log = self._build_run_failure_log_entry(run=run, created_at=max(stage_timestamps.values(), default=getattr(run, "created_at", None)))
        if failure_log:
            logs.append(failure_log)

        logs.sort(key=lambda item: ((item.get("created_at") or getattr(run, "created_at", None) or datetime.min), item.get("type") != "artifact"))
        return logs

    def _build_stage_progress_logs(self, public_steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for step in public_steps:
            grouped.setdefault(step["stage"], []).append(step)

        logs: list[dict[str, Any]] = []
        for stage_name, steps in grouped.items():
            if not steps:
                continue

            latest = steps[-1]
            public_status = build_public_status_payload(stage_name, str(latest.get("status") or ""), latest.get("message"))
            summary = self._build_stage_progress_summary(stage_name, latest, len(steps), public_status)
            logs.append(
                {
                    "type": "status",
                    "stage": stage_name,
                    "stage_label": latest.get("stage_label") or PUBLIC_STAGE_LABELS.get(stage_name, stage_name),
                    "actor_key": latest.get("actor_key"),
                    "actor_name": latest.get("actor_name"),
                    "title": f"{latest.get('stage_label') or PUBLIC_STAGE_LABELS.get(stage_name, stage_name)}阶段记录",
                    "summary": summary,
                    "details": [],
                    "status": latest.get("status"),
                    "created_at": latest.get("created_at"),
                }
            )
        return logs

    def _build_stage_progress_summary(
        self,
        stage_name: str,
        latest_step: dict[str, Any],
        step_count: int,
        public_status: dict[str, Any],
    ) -> str:
        if latest_step.get("event_type") == "status":
            summary = self._normalize_public_text_with_limit(public_status.get("message"), limit=240)
            if summary:
                return summary

        stage_label = latest_step.get("stage_label") or PUBLIC_STAGE_LABELS.get(stage_name, stage_name)
        normalized_status = str(latest_step.get("status") or "").strip().lower()
        if normalized_status == "failed":
            detail = self._normalize_public_text_with_limit(public_status.get("message"), limit=200)
            return detail or f"{stage_label}执行失败。"
        if normalized_status == "success":
            return f"{stage_label}已完成，已记录 {step_count} 个执行动作。"
        if normalized_status == "running":
            return f"{stage_label}进行中，已记录 {step_count} 个执行动作。"
        return f"{stage_label}已记录 {step_count} 个执行动作。"

    def _build_run_failure_log_entry(self, *, run: Any, created_at: Any) -> dict[str, Any] | None:
        if str(getattr(run, "status", "")).strip().lower() != "failed":
            return None

        error_message = self._normalize_public_text_with_limit(getattr(run, "error_message", None), limit=240) or "任务执行失败。"
        return {
            "type": "status",
            "stage": "workflow",
            "stage_label": "任务结果",
            "actor_key": "cao",
            "actor_name": "系统",
            "title": "任务执行失败",
            "summary": error_message,
            "details": [],
            "status": "failed",
            "created_at": created_at or getattr(run, "created_at", None),
        }

    def _build_research_log_entry(self, artifact: dict[str, Any], identity_names: dict[str, str], created_at: Any) -> dict[str, Any] | None:
        hotspots = artifact.get("selected_hotspots") if isinstance(artifact.get("selected_hotspots"), list) else []
        queries = artifact.get("expanded_queries") if isinstance(artifact.get("expanded_queries"), list) else []
        if not hotspots and not queries:
            return None

        details = []
        if queries:
            details.append(f"搜索词：{' / '.join(queries[:6])}")
        for item in hotspots[:6]:
            title = self._normalize_public_text_with_limit(item.get("title"), limit=80) or "热点内容"
            author = self._normalize_public_text_with_limit(item.get("author"), limit=40) or "-"
            details.append(
                f"热点：{title} | 作者：{author} | 热度：{self._format_metric(item.get('heat_score'))} | 播放：{self._format_metric(item.get('view_count'))}"
            )
        return self._build_artifact_log_entry(
            stage="lead.research",
            title="已找到热门视频",
            summary=f"共整理 {len(hotspots)} 条热点候选。",
            details=details,
            identity_names=identity_names,
            created_at=created_at,
        )

    def _build_analysis_log_entry(self, artifact: dict[str, Any], identity_names: dict[str, str], created_at: Any) -> dict[str, Any] | None:
        reports = artifact.get("reports") if isinstance(artifact.get("reports"), list) else []
        if not reports:
            return None

        details = []
        for report in reports[:4]:
            details.append(self._normalize_public_text_with_limit(report.get("report_title"), limit=80) or "爆款DNA报告")
            if report.get("framework_summary"):
                details.append(f"框架：{report['framework_summary']}")
            if report.get("hook_design"):
                details.append(f"钩子：{report['hook_design']}")
            if report.get("emotion_curve"):
                details.append(f"情绪：{report['emotion_curve']}")
            reusable = report.get("reusable_elements") if isinstance(report.get("reusable_elements"), list) else []
            if reusable:
                details.append(f"可复用：{' / '.join(reusable[:6])}")
        return self._build_artifact_log_entry(
            stage="lead.analysis",
            title="爆款基因分析完成",
            summary=f"已输出 {len(reports)} 份爆款 DNA 摘要。",
            details=details,
            identity_names=identity_names,
            created_at=created_at,
        )

    def _build_planning_log_entry(self, artifact: dict[str, Any], identity_names: dict[str, str], created_at: Any) -> dict[str, Any] | None:
        if not artifact:
            return None

        details = []
        for field, label in (
            ("prompt_summary", "策略摘要"),
            ("script_topic", "脚本主题"),
            ("video_prompt", "主提示词"),
        ):
            value = self._normalize_public_text_with_limit(artifact.get(field), limit=240)
            if value:
                details.append(f"{label}：{value}")
        for field, label in (
            ("core_keywords", "核心词"),
            ("hook_keywords", "钩子词"),
            ("visual_keywords", "视觉词"),
            ("title_candidates", "标题候选"),
            ("script_topic_variants", "主题候选"),
            ("video_prompt_variants", "视频变体"),
            ("image_prompt_variants", "图片变体"),
        ):
            values = artifact.get(field) if isinstance(artifact.get(field), list) else []
            if values:
                details.append(f"{label}：{' / '.join(str(item) for item in values[:6])}")
        return self._build_artifact_log_entry(
            stage="lead.research_development",
            title="新提示词已生成",
            summary="技术策划已经完成提示词、标题与视觉指令整理。",
            details=details,
            identity_names=identity_names,
            created_at=created_at,
        )

    def _build_production_log_entry(self, artifact: dict[str, Any], identity_names: dict[str, str], created_at: Any) -> dict[str, Any] | None:
        if not artifact:
            return None

        details = []
        for field, label in (
            ("title", "标题"),
            ("topic", "主题"),
            ("hook", "开头"),
            ("cta", "结尾"),
        ):
            value = self._normalize_public_text_with_limit(artifact.get(field), limit=220)
            if value:
                details.append(f"{label}：{value}")
        tags = artifact.get("tags") if isinstance(artifact.get("tags"), list) else []
        if tags:
            details.append(f"标签：{' / '.join(tags[:8])}")
        scenes = artifact.get("scenes") if isinstance(artifact.get("scenes"), list) else []
        for index, scene in enumerate(scenes[:6], start=1):
            timing = self._normalize_public_text_with_limit(scene.get("timing"), limit=48) or "-"
            visuals = self._normalize_public_text_with_limit(scene.get("visuals"), limit=140) or "-"
            text = self._normalize_public_text_with_limit(scene.get("text"), limit=100) or "-"
            details.append(f"分镜{index}：{timing} | 画面：{visuals} | 字幕：{text}")
        return self._build_artifact_log_entry(
            stage="lead.production",
            title="脚本草案已生成",
            summary=f"已生成 {len(scenes)} 个分镜片段。",
            details=details,
            identity_names=identity_names,
            created_at=created_at,
        )

    def _build_qa_log_entry(self, artifact: dict[str, Any], identity_names: dict[str, str], created_at: Any) -> dict[str, Any] | None:
        if not artifact:
            return None

        details = []
        if artifact.get("recommendation"):
            details.append(f"建议：{artifact['recommendation']}")
        issues = artifact.get("issues") if isinstance(artifact.get("issues"), list) else []
        for issue in issues[:6]:
            details.append(f"检查项：{issue}")
        summary_parts = []
        if "pass" in artifact:
            summary_parts.append("通过" if artifact["pass"] else "未通过")
        if artifact.get("overall_score") is not None:
            summary_parts.append(f"评分 {artifact['overall_score']}")
        return self._build_artifact_log_entry(
            stage="lead.qa",
            title="质检结果已归档",
            summary=" / ".join(summary_parts) or "质检已完成。",
            details=details,
            identity_names=identity_names,
            created_at=created_at,
        )

    def _build_artifact_log_entry(
        self,
        *,
        stage: str,
        title: str,
        summary: str,
        details: list[str],
        identity_names: dict[str, str],
        created_at: Any,
    ) -> dict[str, Any]:
        actor_key = STAGE_IDENTITY_KEYS.get(stage)
        return {
            "type": "artifact",
            "stage": stage,
            "stage_label": PUBLIC_STAGE_LABELS.get(stage, stage),
            "actor_key": actor_key,
            "actor_name": identity_names.get(actor_key, DEFAULT_IDENTITY_NAMES.get(actor_key or "", stage)),
            "title": title,
            "summary": summary,
            "details": details,
            "status": None,
            "created_at": created_at,
        }

    @staticmethod
    def _label_step_status(status: Any) -> str:
        mapping = {
            "running": "进行中",
            "success": "已完成",
            "failed": "失败",
            "idle": "待命",
        }
        normalized = str(status or "").strip().lower()
        return mapping.get(normalized, normalized or "已记录")

    @staticmethod
    def _format_metric(value: Any) -> str:
        if isinstance(value, int):
            return f"{value:,}"
        if isinstance(value, float):
            return f"{value:,.2f}"
        return "-"
