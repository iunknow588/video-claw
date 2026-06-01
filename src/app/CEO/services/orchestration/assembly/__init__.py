from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.CAO.services.publish import PublishService
from app.CCO.services.content_creation import AIAnalysisService
from app.CEO.services.control_plane import control_plane
from app.CEO.services.orchestration.domains.analysis_pipeline import AnalysisPipeline
from app.CEO.services.orchestration.domains.finance_gate import FinanceGate
from app.CEO.services.orchestration.domains.production_pipeline import ProductionPipeline
from app.CEO.services.orchestration.domains.publish_pipeline import PublishPipeline
from app.CEO.services.orchestration.domains.qa_pipeline import QAPipeline
from app.CEO.services.orchestration.domains.rd_pipeline import RDPipeline
from app.CEO.services.orchestration.domains.research_pipeline import ResearchPipeline
from app.CEO.services.orchestration.reroute import QARerouteService, build_default_qa_strategy_registry
from app.CEO.skills.registry import ensure_builtin_skills_registered, registry
from app.CEO.skills.runtime import SkillRuntimeManager
from app.CFO.services.finance import FinanceService
from app.CIO.models.analysis import AnalysisReport
from app.CIO.models.hotspot import HotspotItem
from app.CIO.services.data_access import HotspotRepository
from app.CIO.services.event_bus import EventBus, EventPublisher, EventStore
from app.CIO.services.observability import LogAggregator, MetricsReporter, TraceCollector
from app.CIO.services.workflow_runs import WorkflowRunService
from app.CIO.services.workflow_steps import WorkflowStepLogService
from app.COO.services.script_management import ScriptService
from app.COO.services.video_production import VideoService
from app.CSO.services.hotspot import HotspotService
from app.CSO.services.trend_intelligence import TrendIntelligenceService


class WorkflowAssembly:
    """Builds the service graph and a session-bound skill scope for departmental pipelines."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.recorder = None
        self.control_plane = control_plane
        self.hotspot_service = HotspotService(session)
        self.hotspot_repository = HotspotRepository(session)
        self.analysis_service = AIAnalysisService(session)
        self.script_service = ScriptService(session)
        self.video_service = VideoService(session)
        self.publish_service = PublishService(session)
        self.trend_service = TrendIntelligenceService()
        self.finance_service = FinanceService(session)
        self.workflow_run_service = WorkflowRunService(session)
        self.workflow_step_service = WorkflowStepLogService(session)
        self.log_aggregator = LogAggregator()
        self.event_publisher = EventPublisher()
        self.event_store = EventStore(session, self.log_aggregator)
        self.event_bus = EventBus(self.event_store, self.event_publisher)
        self.trace_collector = TraceCollector(self.workflow_step_service)
        self.metrics_reporter = MetricsReporter()
        self.skill_runtime = SkillRuntimeManager()
        self.skill_registry = registry
        self.qa_reroute_service = QARerouteService(
            self.control_plane,
            strategy_registry=build_default_qa_strategy_registry(),
        )

        ensure_builtin_skills_registered()
        self.skill_scope = registry.bind(session=session)

        self.finance_pipeline = FinanceGate(self)
        self.research_pipeline = ResearchPipeline(self)
        self.analysis_pipeline = AnalysisPipeline(self)
        self.planning_pipeline = RDPipeline(self)
        self.production_pipeline = ProductionPipeline(self)
        self.qa_pipeline = QAPipeline(self)
        self.publish_pipeline = PublishPipeline(self)

    def get_skill(self, name: str) -> Any:
        return self.skill_scope.get(name)

    async def load_hotspot(self, hotspot_id: str) -> HotspotItem:
        hotspot = await self.hotspot_repository.get_by_uuid(hotspot_id)
        if not hotspot:
            raise ValueError(f"Hotspot {hotspot_id} not found")
        return hotspot

    def load_hotspot_sync(self, hotspot_data: dict[str, Any]) -> HotspotItem:
        return HotspotItem(
            uuid=hotspot_data["uuid"],
            content_id=hotspot_data["content_id"],
            platform=hotspot_data["platform"],
            title=hotspot_data.get("title"),
            author=hotspot_data.get("author"),
            category=hotspot_data.get("category"),
            tags=hotspot_data.get("tags", []),
            view_count=hotspot_data.get("view_count", 0),
            like_count=hotspot_data.get("like_count", 0),
            comment_count=hotspot_data.get("comment_count", 0),
            share_count=hotspot_data.get("share_count", 0),
        )

    def serialize_hotspot(self, hotspot: HotspotItem, heat_score: int | None = None) -> dict[str, Any]:
        score = heat_score if heat_score is not None else self.trend_service._calculate_heat_score(hotspot)  # noqa: SLF001
        return {
            "uuid": hotspot.uuid,
            "content_id": hotspot.content_id,
            "platform": hotspot.platform,
            "title": hotspot.title,
            "author": hotspot.author,
            "category": hotspot.category,
            "tags": list(hotspot.tags or []),
            "view_count": int(hotspot.view_count or 0),
            "like_count": int(hotspot.like_count or 0),
            "comment_count": int(hotspot.comment_count or 0),
            "share_count": int(hotspot.share_count or 0),
            "heat_score": score,
        }

    def serialize_analysis(self, report: AnalysisReport) -> dict[str, Any]:
        return {
            "analysis_id": report.uuid,
            "hotspot_id": report.hotspot_id,
            "framework_summary": report.framework_summary,
            "content_structure": report.content_structure,
            "emotion_curve": report.emotion_curve,
            "hook_design": report.hook_design,
            "reusable_elements": list(report.reusable_elements or []),
            "risk_warnings": list(report.risk_warnings or []),
            "api_cost": float(report.api_cost or 0.0),
            "token_usage": dict(getattr(report, "_token_usage", {}) or {}),
        }

    def serialize_script(self, script: Any) -> dict[str, Any]:
        return {
            "uuid": script.uuid,
            "analysis_id": script.analysis_id,
            "content_type": script.content_type,
            "style": script.style,
            "title": script.title,
            "topic": script.topic,
            "duration": script.duration,
            "status": script.status,
            "hook": script.hook,
            "cta": script.cta,
            "tags": list(script.tags or []),
            "version": int(script.version or 1),
            "scenes": list(script.scenes or []),
            "token_usage": dict(getattr(script, "_token_usage", {}) or {}),
        }

    def serialize_video_task(self, task: Any) -> dict[str, Any] | None:
        if task is None:
            return None
        return {
            "uuid": task.uuid,
            "script_id": task.script_id,
            "status": task.status,
            "progress": float(task.progress or 0.0),
            "video_url": task.video_url,
            "style": task.style,
            "size": task.size,
            "quality_score": float(task.quality_score or 0.0) if getattr(task, "quality_score", None) is not None else None,
            "quality_report": dict(task.quality_report or {}) if getattr(task, "quality_report", None) else None,
            "token_usage": dict(getattr(task, "_token_usage", {}) or {}),
        }
