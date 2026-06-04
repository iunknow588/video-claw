from __future__ import annotations

from datetime import UTC, datetime
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

FAILED_STAGE_ALIAS_MAP = {
    "CFO": "lead.cfo",
    "Research": "lead.research",
    "Analysis": "lead.analysis",
    "Planning": "lead.research_development",
    "Production": "lead.production",
    "QA": "lead.qa",
    "Publish": "lead.publish",
}

PUBLIC_SKILL_LABELS = {
    "estimate_cost": "成本估算",
    "verify_balance": "预算校验",
    "charge": "预算扣减",
    "domain_query_expansion": "检索词扩展",
    "hotspot_collection": "热点采集",
    "hotspot_dedup": "热点去重",
    "hotspot_ranking": "热点排序",
    "hotspot_snapshot": "热点归档",
    "material_search": "素材检索",
    "hotspot_structure": "结构拆解",
    "hook_extraction": "钩子提取",
    "emotion_curve": "情绪曲线分析",
    "risk_extraction": "风险提取",
    "reusable_element": "可复用元素提炼",
    "analysis_persist": "分析结果归档",
    "prompt_package": "提示词包生成",
    "title_candidate": "标题候选生成",
    "prompt_validation": "提示词校验",
    "prompt_version": "提示词版本归档",
    "script_draft": "脚本草案生成",
    "subtitle_compose": "字幕合成",
    "voiceover_generate": "配音生成",
    "video_compose_plan": "视频合成规划",
    "render_execute": "渲染执行",
    "asset_storage": "资产入库",
    "retry_recovery": "重试恢复",
    "video_quality_check": "画面质量检查",
    "content_compliance_check": "内容合规检查",
    "gene_alignment_check": "爆款基因对齐检查",
    "technical_spec_check": "技术规格检查",
    "delivery_asset_check": "交付资产检查",
    "render_output_check": "渲染结果检查",
    "qa_report": "质检报告生成",
    "publish_plan": "发布计划生成",
    "platform_adapter": "平台适配",
    "publish_execute": "发布执行",
    "publish_callback": "发布回调登记",
    "publish_history": "发布历史归档",
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

        return self._serialize_public_payload(
            {
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
        )

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
        return self._serialize_public_payload([self._serialize_public_run(run) for run in runs])

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

        public_artifacts = self._build_public_artifacts(result_payload)

        return self._serialize_public_payload(
            {
                "run": self._serialize_public_run(run),
                "summary": {
                    "trace_id": summary.get("trace_id"),
                    "step_count": summary.get("step_count", 0),
                    "total_cost": summary.get("total_cost", 0),
                    "total_tokens": summary.get("total_tokens", 0),
                    "token_usage_by_lead": summary.get("token_usage_by_lead", {}),
                    "token_usage_by_skill": summary.get("token_usage_by_skill", {}),
                    "failed_steps": summary.get("failed_steps", []),
                    "started_at": summary.get("started_at"),
                    "finished_at": summary.get("finished_at"),
                    "stage_statuses": {
                        item["name"]: item["status"] for item in public_stage_statuses
                    },
                    "pipeline_order": [item["name"] for item in public_stage_statuses],
                },
                "identity_settings": identity_settings,
                "public_stage_statuses": public_stage_statuses,
                "public_steps": public_steps,
                "public_artifacts": public_artifacts,
                "public_logs": self._build_public_logs(
                    run=run,
                    raw_steps=steps,
                    public_steps=public_steps,
                    public_artifacts=public_artifacts,
                    identity_names=names,
                ),
            }
        )

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
            local_created_at = self._to_local_display_datetime(created_at)
            return f"{platform_label}任务 {local_created_at.strftime('%m-%d %H:%M')}"
        return f"{platform_label}任务"

    @staticmethod
    def _to_local_display_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone()

    def _serialize_public_payload(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return self._to_local_display_datetime(value).isoformat(timespec="seconds")
        if isinstance(value, dict):
            return {
                key: self._serialize_public_payload(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._serialize_public_payload(item) for item in value]
        if isinstance(value, tuple):
            return [self._serialize_public_payload(item) for item in value]
        return value

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
        # 正常流程的产物
        research_bundle = result_payload.get("research_bundle") if isinstance(result_payload.get("research_bundle"), dict) else {}
        analysis_bundle = result_payload.get("analysis_bundle") if isinstance(result_payload.get("analysis_bundle"), dict) else {}
        prompt_package = result_payload.get("prompt_package") if isinstance(result_payload.get("prompt_package"), dict) else {}
        production_bundle = result_payload.get("production_bundle") if isinstance(result_payload.get("production_bundle"), dict) else {}
        qa_bundle = result_payload.get("qa_bundle") if isinstance(result_payload.get("qa_bundle"), dict) else {}
        
        # 失败流程的产物（从 failure_context 中提取）
        failure_context = result_payload.get("failure_context", {})
        if not isinstance(failure_context, dict) or not failure_context:
            failure_context = result_payload
        if failure_context:
            research_bundle = research_bundle or failure_context.get("research_bundle", {})
            analysis_bundle = analysis_bundle or failure_context.get("analysis_bundle", {})
            prompt_package = prompt_package or failure_context.get("prompt_bundle", {})
            production_bundle = production_bundle or failure_context.get("production_bundle", {})
            qa_bundle = qa_bundle or failure_context.get("qa_bundle", {})

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
                for item in hotspot_items[:8]
                if (serialized := self._serialize_public_hotspot(item)) is not None
            ]
            if serialized_hotspots:
                research_artifact["selected_hotspots"] = serialized_hotspots

        hotspot_pool = research_bundle.get("hotspot_pool")
        if isinstance(hotspot_pool, list):
            serialized_pool = [
                serialized
                for item in hotspot_pool[:12]
                if (serialized := self._serialize_public_hotspot(item)) is not None
            ]
            if serialized_pool:
                research_artifact["hotspot_pool"] = serialized_pool

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

        publish_bundle = result_payload.get("publish_bundle") if isinstance(result_payload.get("publish_bundle"), dict) else {}
        if failure_context:
            publish_bundle = publish_bundle or failure_context.get("publish_bundle", {})
        publish_artifact = self._serialize_public_publish_bundle(publish_bundle)
        if publish_artifact:
            public_artifacts["publish"] = publish_artifact

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

        version_label = self._normalize_public_text_with_limit(item.get("version_label"), limit=48)
        if version_label:
            payload["version_label"] = version_label

        fingerprint = self._normalize_public_text_with_limit(item.get("fingerprint"), limit=24)
        if fingerprint:
            payload["fingerprint"] = fingerprint

        quality_score = item.get("quality_score")
        if isinstance(quality_score, (int, float)):
            payload["quality_score"] = round(float(quality_score), 4)

        for field in ("core_keywords", "hook_keywords", "visual_keywords", "title_candidates", "script_topic_variants"):
            values = self._normalize_public_list(item.get(field), limit=6, max_length=40)
            if values:
                payload[field] = values

        for field in ("video_prompt_variants", "image_prompt_variants"):
            values = self._normalize_public_list(item.get(field), limit=3, max_length=180)
            if values:
                payload[field] = values

        for field in ("validation_issues", "validation_warnings"):
            values = self._normalize_public_list(item.get(field), limit=6, max_length=120)
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

        material_bundle = item.get("material_bundle") if isinstance(item.get("material_bundle"), dict) else {}
        material_candidates = material_bundle.get("material_candidates")
        if isinstance(material_candidates, list):
            serialized_candidates = [
                serialized
                for candidate in material_candidates[:8]
                if (serialized := self._serialize_public_material_candidate(candidate)) is not None
            ]
            if serialized_candidates:
                payload["material_candidates"] = serialized_candidates

        subtitle_bundle = item.get("subtitle_bundle") if isinstance(item.get("subtitle_bundle"), dict) else {}
        subtitle_file = self._normalize_public_text_with_limit(subtitle_bundle.get("subtitle_file"), limit=180)
        if subtitle_file:
            payload["subtitle_file"] = subtitle_file
        subtitle_items = subtitle_bundle.get("subtitle_items")
        if isinstance(subtitle_items, list):
            payload["subtitle_count"] = len(subtitle_items)

        voiceover_bundle = item.get("voiceover_bundle") if isinstance(item.get("voiceover_bundle"), dict) else {}
        audio_file = self._normalize_public_text_with_limit(voiceover_bundle.get("audio_file"), limit=180)
        if audio_file:
            payload["audio_file"] = audio_file
        voice_profile = self._normalize_public_text_with_limit(voiceover_bundle.get("voice_profile"), limit=64)
        if voice_profile:
            payload["voice_profile"] = voice_profile
        voice_segments = voiceover_bundle.get("voice_segments")
        if isinstance(voice_segments, list):
            payload["voice_segment_count"] = len(voice_segments)

        composition_bundle = item.get("composition_bundle") if isinstance(item.get("composition_bundle"), dict) else {}
        ffmpeg_plan = composition_bundle.get("ffmpeg_plan") if isinstance(composition_bundle.get("ffmpeg_plan"), dict) else {}
        ffmpeg_inputs = self._normalize_public_list(ffmpeg_plan.get("inputs"), limit=8, max_length=120)
        if ffmpeg_inputs:
            payload["composition_inputs"] = ffmpeg_inputs
        ffmpeg_filters = self._normalize_public_list(ffmpeg_plan.get("filters"), limit=8, max_length=64)
        if ffmpeg_filters:
            payload["composition_filters"] = ffmpeg_filters

        render_bundle = item.get("render_bundle") if isinstance(item.get("render_bundle"), dict) else {}
        render_mode = self._normalize_public_text_with_limit(render_bundle.get("render_mode"), limit=64)
        if render_mode:
            payload["render_mode"] = render_mode
        delivery_asset_url = self._normalize_public_text_with_limit(render_bundle.get("delivery_asset_url"), limit=240)
        if delivery_asset_url:
            payload["delivery_asset_url"] = delivery_asset_url

        return payload

    def _serialize_public_material_candidate(self, item: Any) -> dict[str, Any] | None:
        if not isinstance(item, dict):
            return None

        payload: dict[str, Any] = {}
        for field in ("title", "source", "type", "cache_path", "provider"):
            value = self._normalize_public_text_with_limit(item.get(field), limit=120)
            if value:
                payload[field] = value
        url = self._normalize_public_text_with_limit(item.get("url"), limit=240)
        if url:
            payload["url"] = url
        duration = item.get("duration")
        if isinstance(duration, (int, float)):
            payload["duration"] = duration
        return payload or None

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

        checks = item.get("checks") if isinstance(item.get("checks"), list) else []
        check_summaries: list[str] = []
        for check in checks[:8]:
            if not isinstance(check, dict):
                continue
            dimension = self._normalize_public_text_with_limit(check.get("dimension"), limit=48) or "unknown"
            status = "通过" if check.get("pass") else "未通过"
            issue_list = check.get("issues") if isinstance(check.get("issues"), list) else []
            issue_text = "；".join(str(entry) for entry in issue_list[:2]) if issue_list else ""
            summary = f"{dimension}：{status}"
            if issue_text:
                summary = f"{summary} | {issue_text}"
            check_summaries.append(summary[:200])
        if check_summaries:
            payload["checks"] = check_summaries

        return payload

    def _serialize_public_publish_bundle(self, item: dict[str, Any]) -> dict[str, Any]:
        bundle = item.get("bundle") if isinstance(item.get("bundle"), dict) else item
        if not isinstance(bundle, dict):
            return {}

        payload: dict[str, Any] = {}

        publish_plan = bundle.get("publish_plan") if isinstance(bundle.get("publish_plan"), dict) else {}
        for field in ("platform", "publish_goal", "audience", "video_url", "video_task_id", "target_status"):
            limit = 240 if field == "video_url" else 120
            value = self._normalize_public_text_with_limit(publish_plan.get(field), limit=limit)
            if value:
                payload[field] = value
        publish_steps = self._normalize_public_list(publish_plan.get("publish_steps"), limit=8, max_length=48)
        if publish_steps:
            payload["publish_steps"] = publish_steps

        platform_payload = bundle.get("platform_payload") if isinstance(bundle.get("platform_payload"), dict) else {}
        for field in ("adapter_name", "mode"):
            value = self._normalize_public_text_with_limit(platform_payload.get(field), limit=64)
            if value:
                payload[field] = value

        publish_result = bundle.get("publish_result") if isinstance(bundle.get("publish_result"), dict) else {}
        for field in ("publish_id", "status"):
            value = self._normalize_public_text_with_limit(publish_result.get(field), limit=120)
            if value:
                payload[field] = value

        callback = bundle.get("callback") if isinstance(bundle.get("callback"), dict) else {}
        callback_status = self._normalize_public_text_with_limit(callback.get("callback_status"), limit=64)
        if callback_status:
            payload["callback_status"] = callback_status
        callback_ref = self._normalize_public_text_with_limit(callback.get("callback_ref"), limit=120)
        if callback_ref:
            payload["callback_ref"] = callback_ref

        history = bundle.get("history") if isinstance(bundle.get("history"), dict) else {}
        history_status = self._normalize_public_text_with_limit(history.get("history_status"), limit=64)
        if history_status:
            payload["history_status"] = history_status
        history_ref = self._normalize_public_text_with_limit(history.get("history_ref"), limit=120)
        if history_ref:
            payload["history_ref"] = history_ref

        retry = bundle.get("retry") if isinstance(bundle.get("retry"), dict) else {}
        if "retry" in retry:
            payload["retry"] = bool(retry.get("retry"))

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
        raw_steps: list[Any],
        public_steps: list[dict[str, Any]],
        public_artifacts: dict[str, Any],
        identity_names: dict[str, str],
    ) -> list[dict[str, Any]]:
        stage_timestamps: dict[str, Any] = {}
        for step in public_steps:
            stage_timestamps[step["stage"]] = step.get("created_at") or stage_timestamps.get(step["stage"])

        logs = self._build_stage_progress_logs(public_steps)
        logs.extend(self._build_skill_diagnostic_logs(raw_steps, identity_names))

        logs.extend(self._build_research_log_entries(public_artifacts.get("research") or {}, identity_names, stage_timestamps.get("lead.research")))
        logs.extend(self._build_analysis_log_entries(public_artifacts.get("analysis") or {}, identity_names, stage_timestamps.get("lead.analysis")))
        logs.extend(self._build_planning_log_entries(public_artifacts.get("planning") or {}, identity_names, stage_timestamps.get("lead.research_development")))
        logs.extend(self._build_production_log_entries(public_artifacts.get("production") or {}, identity_names, stage_timestamps.get("lead.production")))
        logs.extend(self._build_qa_log_entries(public_artifacts.get("qa") or {}, identity_names, stage_timestamps.get("lead.qa")))
        logs.extend(self._build_publish_log_entries(public_artifacts.get("publish") or {}, identity_names, stage_timestamps.get("lead.publish")))

        failure_log = self._build_run_failure_log_entry(run=run, created_at=max(stage_timestamps.values(), default=getattr(run, "created_at", None)))
        if failure_log:
            logs.append(failure_log)

        logs.sort(key=lambda item: ((item.get("created_at") or getattr(run, "created_at", None) or datetime.min), item.get("type") != "artifact"))
        return logs

    def _build_skill_diagnostic_logs(self, raw_steps: list[Any], identity_names: dict[str, str]) -> list[dict[str, Any]]:
        grouped_steps: dict[tuple[str, str], list[Any]] = {}
        for step in raw_steps:
            skill_name = str(getattr(step, "skill_name", "") or "")
            if not skill_name.startswith("lead.") or skill_name.count(".") < 2:
                continue
            if getattr(step, "event_type", None) not in {"finish", "fail"}:
                continue
            stage_name = self._to_stage_name(skill_name)
            if stage_name not in PUBLIC_STAGE_LABELS:
                continue
            grouped_steps.setdefault((stage_name, skill_name), []).append(step)

        logs: list[dict[str, Any]] = []
        for (stage_name, skill_name), steps in grouped_steps.items():
            latest = steps[-1]
            latest_output = latest.output_json if isinstance(latest.output_json, dict) else {}
            latest_input = latest.input_json if isinstance(latest.input_json, dict) else {}
            actor_key = STAGE_IDENTITY_KEYS.get(stage_name)
            details = [f"技能标识：{skill_name}", f"累计执行：{len(steps)} 次"]

            input_summary = self._summarize_public_value(
                self._build_step_debug_summary(latest_input),
                max_length=220,
            )
            if input_summary:
                details.append(f"最近输入：{input_summary}")

            recent_samples = steps[-3:]
            for index, step in enumerate(recent_samples, start=max(len(steps) - len(recent_samples) + 1, 1)):
                output_json = step.output_json if isinstance(step.output_json, dict) else {}
                output_summary = self._summarize_public_value(
                    self._build_step_debug_summary(output_json),
                    max_length=220,
                )
                if output_summary:
                    details.append(f"执行 {index} 输出：{output_summary}")
                elif getattr(step, "error_message", None):
                    error_summary = self._normalize_public_text_with_limit(step.error_message, limit=220)
                    if error_summary:
                        details.append(f"执行 {index} 错误：{error_summary}")

            summary = self._build_skill_diagnostic_summary(latest, steps)
            logs.append(
                {
                    "type": "artifact",
                    "stage": stage_name,
                    "stage_label": PUBLIC_STAGE_LABELS.get(stage_name, stage_name),
                    "actor_key": actor_key,
                    "actor_name": identity_names.get(actor_key, DEFAULT_IDENTITY_NAMES.get(actor_key or "", stage_name)),
                    "title": f"技能执行：{self._label_skill_name(skill_name)}",
                    "summary": summary,
                    "details": details,
                    "status": getattr(latest, "status", None),
                    "created_at": getattr(latest, "created_at", None),
                }
            )
        return logs

    def _build_step_debug_summary(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not payload:
            return None
        ignored_keys = {"trace_id", "workflow_run_id", "hotspots", "reports", "analysis_reports", "snapshot"}
        summary: dict[str, Any] = {}
        for key, value in payload.items():
            if key in ignored_keys:
                continue
            if isinstance(value, list):
                normalized_list = self._normalize_public_list(value, limit=4, max_length=60)
                if normalized_list:
                    summary[key] = normalized_list
            elif isinstance(value, dict):
                nested_summary = self._summarize_public_value(value, max_length=120)
                if nested_summary:
                    summary[key] = nested_summary
            else:
                normalized = self._summarize_public_value(value, max_length=80)
                if normalized:
                    summary[key] = normalized
            if len(summary) >= 6:
                break
        return summary or None

    def _build_skill_diagnostic_summary(self, latest: Any, steps: list[Any]) -> str:
        status = str(getattr(latest, "status", "") or "").strip().lower()
        if status == "failed":
            error_summary = self._normalize_public_text_with_limit(getattr(latest, "error_message", None), limit=220)
            return error_summary or f"最近一次执行失败，共记录 {len(steps)} 次技能调用。"
        if status == "success":
            return f"最近一次执行成功，共记录 {len(steps)} 次技能调用。"
        return f"已记录 {len(steps)} 次技能调用。"

    def _label_skill_name(self, skill_name: str) -> str:
        tail = skill_name.rsplit(".", maxsplit=1)[-1]
        return PUBLIC_SKILL_LABELS.get(tail, tail.replace("_", " "))

    def _build_stage_progress_logs(self, public_steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for step in public_steps:
            grouped.setdefault(step["stage"], []).append(step)

        logs: list[dict[str, Any]] = []
        for stage_name, steps in grouped.items():
            if not steps:
                continue

            latest = steps[-1]
            latest_status_step = next(
                (step for step in reversed(steps) if step.get("event_type") == "status"),
                latest,
            )
            public_status = build_public_status_payload(
                stage_name,
                str(latest_status_step.get("status") or ""),
                latest_status_step.get("message"),
            )
            summary = self._build_stage_progress_summary(stage_name, latest_status_step, len(steps), public_status)
            logs.append(
                {
                    "type": "status",
                    "stage": stage_name,
                    "stage_label": latest_status_step.get("stage_label") or PUBLIC_STAGE_LABELS.get(stage_name, stage_name),
                    "actor_key": latest_status_step.get("actor_key"),
                    "actor_name": latest_status_step.get("actor_name"),
                    "title": f"{latest_status_step.get('stage_label') or PUBLIC_STAGE_LABELS.get(stage_name, stage_name)}阶段记录",
                    "summary": summary,
                    "details": [],
                    "status": latest_status_step.get("status"),
                    "created_at": latest_status_step.get("created_at"),
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

        result_payload = run.result_payload if isinstance(run.result_payload, dict) else {}
        failure_context = result_payload.get("failure_context", {})
        if not isinstance(failure_context, dict) or not failure_context:
            failure_context = result_payload
        
        # 构建可读的错误详情
        details = []
        
        # 如果有 QA 失败维度，展示具体原因
        qa_checks = failure_context.get("qa_checks", [])
        failed_checks = [c for c in qa_checks if c.get("applicable") and not c.get("pass")]
        for check in failed_checks:
            dimension = check.get("dimension", "未知维度")
            issues = check.get("issues", [])
            score = check.get("score", 0)
            issues_text = "；".join(issues) if issues else "未通过"
            details.append(f"【{dimension}】评分 {score}：{issues_text}")
        
        # 如果有失败阶段信息，添加阶段提示
        failed_stage = failure_context.get("failed_stage")
        if failed_stage and failed_stage != "unknown":
            normalized_failed_stage = FAILED_STAGE_ALIAS_MAP.get(str(failed_stage), str(failed_stage))
            stage_label = PUBLIC_STAGE_LABELS.get(normalized_failed_stage, normalized_failed_stage)
            details.insert(0, f"失败阶段：{stage_label}")
        
        # 通用错误信息
        error_message = self._normalize_public_text_with_limit(
            getattr(run, "error_message", None), 
            limit=240
        ) or self._normalize_public_text_with_limit(
            failure_context.get("error"),
            limit=240,
        ) or "任务执行失败。"

        return {
            "type": "status",
            "stage": "workflow",
            "stage_label": "任务结果",
            "actor_key": "cao",
            "actor_name": "系统",
            "title": "任务执行失败",
            "summary": error_message,
            "details": details,  # 前台可展开查看具体失败维度
            "status": "failed",
            "created_at": created_at or getattr(run, "created_at", None),
        }

    def _build_research_log_entries(self, artifact: dict[str, Any], identity_names: dict[str, str], created_at: Any) -> list[dict[str, Any]]:
        logs: list[dict[str, Any]] = []
        summary_entry = self._build_research_log_entry(artifact, identity_names, created_at)
        if summary_entry:
            logs.append(summary_entry)

        queries = artifact.get("expanded_queries") if isinstance(artifact.get("expanded_queries"), list) else []
        if queries:
            logs.append(
                self._build_artifact_log_entry(
                    stage="lead.research",
                    title="检索词已展开",
                    summary=f"共生成 {len(queries)} 组检索词。",
                    details=[f"检索词 {index}：{query}" for index, query in enumerate(queries[:12], start=1)],
                    identity_names=identity_names,
                    created_at=created_at,
                )
            )

        pool_source = artifact.get("hotspot_pool") if isinstance(artifact.get("hotspot_pool"), list) else []
        if not pool_source:
            pool_source = artifact.get("selected_hotspots") if isinstance(artifact.get("selected_hotspots"), list) else []
        if pool_source:
            logs.append(
                self._build_artifact_log_entry(
                    stage="lead.research",
                    title="热点候选池已归档",
                    summary=f"候选池共保留 {len(pool_source)} 条结果。",
                    details=[
                        (
                            f"候选 {index}："
                            f"{self._normalize_public_text_with_limit(item.get('title'), limit=72) or '热点内容'}"
                            f" | 作者：{self._normalize_public_text_with_limit(item.get('author'), limit=32) or '-'}"
                            f" | 热度：{self._format_metric(item.get('heat_score'))}"
                            f" | 播放：{self._format_metric(item.get('view_count'))}"
                        )
                        for index, item in enumerate(pool_source[:12], start=1)
                    ],
                    identity_names=identity_names,
                    created_at=created_at,
                )
            )
        return logs

    def _build_analysis_log_entries(self, artifact: dict[str, Any], identity_names: dict[str, str], created_at: Any) -> list[dict[str, Any]]:
        logs: list[dict[str, Any]] = []
        summary_entry = self._build_analysis_log_entry(artifact, identity_names, created_at)
        if summary_entry:
            logs.append(summary_entry)

        reports = artifact.get("reports") if isinstance(artifact.get("reports"), list) else []
        for index, report in enumerate(reports[:6], start=1):
            report_details = []
            for field, label in (
                ("framework_summary", "结构框架"),
                ("hook_design", "钩子设计"),
                ("emotion_curve", "情绪曲线"),
            ):
                value = self._normalize_public_text_with_limit(report.get(field), limit=180)
                if value:
                    report_details.append(f"{label}：{value}")
            reusable = report.get("reusable_elements") if isinstance(report.get("reusable_elements"), list) else []
            if reusable:
                report_details.append(f"可复用元素：{' / '.join(reusable[:6])}")
            risk_warnings = report.get("risk_warnings") if isinstance(report.get("risk_warnings"), list) else []
            if risk_warnings:
                report_details.append(f"风险提醒：{' / '.join(risk_warnings[:4])}")
            logs.append(
                self._build_artifact_log_entry(
                    stage="lead.analysis",
                    title=f"分析报告 {index}",
                    summary=self._normalize_public_text_with_limit(report.get("report_title"), limit=120) or f"第 {index} 份分析报告",
                    details=report_details,
                    identity_names=identity_names,
                    created_at=created_at,
                )
            )
        return logs

    def _build_planning_log_entries(self, artifact: dict[str, Any], identity_names: dict[str, str], created_at: Any) -> list[dict[str, Any]]:
        logs: list[dict[str, Any]] = []
        summary_entry = self._build_planning_log_entry(artifact, identity_names, created_at)
        if summary_entry:
            logs.append(summary_entry)

        keyword_details = []
        for field, label in (
            ("core_keywords", "核心词"),
            ("hook_keywords", "钩子词"),
            ("visual_keywords", "视觉词"),
        ):
            values = artifact.get(field) if isinstance(artifact.get(field), list) else []
            if values:
                keyword_details.append(f"{label}：{' / '.join(str(item) for item in values[:8])}")
        if keyword_details:
            logs.append(
                self._build_artifact_log_entry(
                    stage="lead.research_development",
                    title="提示词关键词包已归档",
                    summary="关键词、钩子词和视觉词已经整理完成。",
                    details=keyword_details,
                    identity_names=identity_names,
                    created_at=created_at,
                )
            )

        variant_details = []
        for field, label in (
            ("title_candidates", "标题候选"),
            ("script_topic_variants", "主题候选"),
            ("video_prompt_variants", "视频提示词"),
            ("image_prompt_variants", "图片提示词"),
        ):
            values = artifact.get(field) if isinstance(artifact.get(field), list) else []
            for index, value in enumerate(values[:6], start=1):
                variant_details.append(f"{label} {index}：{value}")
        for item in (artifact.get("validation_warnings") if isinstance(artifact.get("validation_warnings"), list) else [])[:4]:
            variant_details.append(f"校验提醒：{item}")
        for item in (artifact.get("validation_issues") if isinstance(artifact.get("validation_issues"), list) else [])[:4]:
            variant_details.append(f"校验问题：{item}")
        if variant_details:
            logs.append(
                self._build_artifact_log_entry(
                    stage="lead.research_development",
                    title="提示词变体与校验结果",
                    summary="提示词候选、变体和校验结果均已记录。",
                    details=variant_details,
                    identity_names=identity_names,
                    created_at=created_at,
                )
            )
        return logs

    def _build_production_log_entries(self, artifact: dict[str, Any], identity_names: dict[str, str], created_at: Any) -> list[dict[str, Any]]:
        logs: list[dict[str, Any]] = []
        summary_entry = self._build_production_log_entry(artifact, identity_names, created_at)
        if summary_entry:
            logs.append(summary_entry)

        material_candidates = artifact.get("material_candidates") if isinstance(artifact.get("material_candidates"), list) else []
        if material_candidates:
            logs.append(
                self._build_artifact_log_entry(
                    stage="lead.production",
                    title="素材候选已整理",
                    summary=f"共准备 {len(material_candidates)} 条素材候选。",
                    details=[
                        (
                            f"素材 {index}："
                            f"{self._normalize_public_text_with_limit(item.get('title'), limit=72) or '-'}"
                            f" | 来源：{self._normalize_public_text_with_limit(item.get('source'), limit=32) or '-'}"
                            f" | 类型：{self._normalize_public_text_with_limit(item.get('type'), limit=24) or '-'}"
                        )
                        for index, item in enumerate(material_candidates[:8], start=1)
                    ],
                    identity_names=identity_names,
                    created_at=created_at,
                )
            )

        asset_details = []
        if artifact.get("subtitle_file"):
            asset_details.append(f"字幕文件：{artifact['subtitle_file']}")
        if artifact.get("subtitle_count") is not None:
            asset_details.append(f"字幕条数：{artifact['subtitle_count']}")
        if artifact.get("audio_file"):
            asset_details.append(f"配音文件：{artifact['audio_file']}")
        if artifact.get("voice_profile"):
            asset_details.append(f"音色：{artifact['voice_profile']}")
        if artifact.get("voice_segment_count") is not None:
            asset_details.append(f"配音片段：{artifact['voice_segment_count']}")
        if asset_details:
            logs.append(
                self._build_artifact_log_entry(
                    stage="lead.production",
                    title="字幕与配音资产已生成",
                    summary="字幕和配音资产已经落盘，可继续进入合成。",
                    details=asset_details,
                    identity_names=identity_names,
                    created_at=created_at,
                )
            )

        compose_details = []
        composition_inputs = artifact.get("composition_inputs") if isinstance(artifact.get("composition_inputs"), list) else []
        composition_filters = artifact.get("composition_filters") if isinstance(artifact.get("composition_filters"), list) else []
        if composition_inputs:
            compose_details.append(f"合成输入：{' / '.join(composition_inputs[:8])}")
        if composition_filters:
            compose_details.append(f"滤镜链：{' / '.join(composition_filters[:8])}")
        if artifact.get("render_mode"):
            compose_details.append(f"渲染模式：{artifact['render_mode']}")
        if artifact.get("delivery_asset_url"):
            compose_details.append(f"交付地址：{artifact['delivery_asset_url']}")
        if compose_details:
            logs.append(
                self._build_artifact_log_entry(
                    stage="lead.production",
                    title="合成与渲染计划已生成",
                    summary="合成输入、滤镜链和渲染输出已记录。",
                    details=compose_details,
                    identity_names=identity_names,
                    created_at=created_at,
                )
            )
        return logs

    def _build_qa_log_entries(self, artifact: dict[str, Any], identity_names: dict[str, str], created_at: Any) -> list[dict[str, Any]]:
        logs: list[dict[str, Any]] = []
        summary_entry = self._build_qa_log_entry(artifact, identity_names, created_at)
        if summary_entry:
            logs.append(summary_entry)

        checks = artifact.get("checks") if isinstance(artifact.get("checks"), list) else []
        if checks:
            logs.append(
                self._build_artifact_log_entry(
                    stage="lead.qa",
                    title="质检检查项明细",
                    summary=f"共记录 {len(checks)} 条质检检查项。",
                    details=[f"检查项 {index}：{check}" for index, check in enumerate(checks[:8], start=1)],
                    identity_names=identity_names,
                    created_at=created_at,
                )
            )
        return logs

    def _build_publish_log_entries(self, artifact: dict[str, Any], identity_names: dict[str, str], created_at: Any) -> list[dict[str, Any]]:
        logs: list[dict[str, Any]] = []
        summary_entry = self._build_publish_log_entry(artifact, identity_names, created_at)
        if summary_entry:
            logs.append(summary_entry)

        plan_details = []
        for field, label in (
            ("platform", "平台"),
            ("publish_goal", "发布目标"),
            ("audience", "受众"),
            ("video_url", "交付视频"),
            ("video_task_id", "视频任务"),
            ("target_status", "目标状态"),
        ):
            value = self._normalize_public_text_with_limit(artifact.get(field), limit=240)
            if value:
                plan_details.append(f"{label}：{value}")
        publish_steps = artifact.get("publish_steps") if isinstance(artifact.get("publish_steps"), list) else []
        if publish_steps:
            plan_details.append(f"发布步骤：{' / '.join(str(item) for item in publish_steps[:8])}")
        if plan_details:
            logs.append(
                self._build_artifact_log_entry(
                    stage="lead.publish",
                    title="发布计划已生成",
                    summary="平台、受众、交付视频和发布步骤已经整理完成。",
                    details=plan_details,
                    identity_names=identity_names,
                    created_at=created_at,
                )
            )

        adapter_details = []
        for field, label in (
            ("adapter_name", "适配器"),
            ("mode", "适配模式"),
        ):
            value = self._normalize_public_text_with_limit(artifact.get(field), limit=120)
            if value:
                adapter_details.append(f"{label}：{value}")
        if adapter_details:
            logs.append(
                self._build_artifact_log_entry(
                    stage="lead.publish",
                    title="平台适配结果已归档",
                    summary="平台适配参数已经记录，可用于复盘投递行为。",
                    details=adapter_details,
                    identity_names=identity_names,
                    created_at=created_at,
                )
            )

        result_details = []
        for field, label in (
            ("publish_id", "发布单号"),
            ("status", "发布状态"),
            ("callback_status", "回调状态"),
            ("callback_ref", "回调引用"),
            ("history_status", "历史归档"),
            ("history_ref", "历史引用"),
        ):
            value = self._normalize_public_text_with_limit(artifact.get(field), limit=160)
            if value:
                result_details.append(f"{label}：{value}")
        if "retry" in artifact:
            result_details.append(f"是否重试：{'是' if artifact.get('retry') else '否'}")
        if result_details:
            logs.append(
                self._build_artifact_log_entry(
                    stage="lead.publish",
                    title="发布结果已记录",
                    summary="发布执行结果、回调状态和归档信息已经记录。",
                    details=result_details,
                    identity_names=identity_names,
                    created_at=created_at,
                )
            )
        return logs

    def _build_research_log_entry(self, artifact: dict[str, Any], identity_names: dict[str, str], created_at: Any) -> dict[str, Any] | None:
        hotspots = artifact.get("selected_hotspots") if isinstance(artifact.get("selected_hotspots"), list) else []
        queries = artifact.get("expanded_queries") if isinstance(artifact.get("expanded_queries"), list) else []
        hotspot_pool = artifact.get("hotspot_pool") if isinstance(artifact.get("hotspot_pool"), list) else []
        if not hotspots and not queries and not hotspot_pool:
            return None

        details = []
        if queries:
            details.append(f"搜索词：{' / '.join(queries[:6])}")
        for index, item in enumerate(hotspot_pool[:8], start=1):
            title = self._normalize_public_text_with_limit(item.get("title"), limit=80) or "候选内容"
            author = self._normalize_public_text_with_limit(item.get("author"), limit=40) or "-"
            details.append(
                f"候选{index}：{title} | 作者：{author} | 热度：{self._format_metric(item.get('heat_score'))} | 播放：{self._format_metric(item.get('view_count'))}"
            )
        for item in hotspots[:6]:
            title = self._normalize_public_text_with_limit(item.get("title"), limit=80) or "热点内容"
            author = self._normalize_public_text_with_limit(item.get("author"), limit=40) or "-"
            details.append(
                f"热点：{title} | 作者：{author} | 热度：{self._format_metric(item.get('heat_score'))} | 播放：{self._format_metric(item.get('view_count'))}"
            )
        return self._build_artifact_log_entry(
            stage="lead.research",
            title="已找到热门视频",
            summary=f"共整理 {len(hotspots)} 条入选热点，候选池 {len(hotspot_pool)} 条。",
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
        if isinstance(artifact.get("quality_score"), (int, float)):
            details.append(f"质量分：{round(float(artifact['quality_score']), 4)}")
        version_label = self._normalize_public_text_with_limit(artifact.get("version_label"), limit=48)
        if version_label:
            details.append(f"版本：{version_label}")
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

    def _build_publish_log_entry(self, artifact: dict[str, Any], identity_names: dict[str, str], created_at: Any) -> dict[str, Any] | None:
        if not artifact:
            return None

        details = []
        for field, label in (
            ("platform", "平台"),
            ("publish_goal", "发布目标"),
            ("audience", "受众"),
            ("publish_id", "发布单号"),
        ):
            value = self._normalize_public_text_with_limit(artifact.get(field), limit=180)
            if value:
                details.append(f"{label}：{value}")

        summary_parts = []
        status = self._normalize_public_text_with_limit(artifact.get("status"), limit=64)
        if status:
            summary_parts.append(f"发布状态 {status}")
        callback_status = self._normalize_public_text_with_limit(artifact.get("callback_status"), limit=64)
        if callback_status:
            summary_parts.append(f"回调 {callback_status}")
        history_status = self._normalize_public_text_with_limit(artifact.get("history_status"), limit=64)
        if history_status:
            summary_parts.append(f"归档 {history_status}")

        return self._build_artifact_log_entry(
            stage="lead.publish",
            title="对外交付结果已归档",
            summary=" / ".join(summary_parts) or "发布链路已完成。",
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
