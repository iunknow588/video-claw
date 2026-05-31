from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AnalysisReport
from app.models.hotspot import HotspotItem
from app.Analysis.skills import (
    AnalysisPersistSkill,
    EmotionCurveSkill,
    HookExtractionSkill,
    HotspotStructureSkill,
    ReusableElementSkill,
    RiskExtractionSkill,
)
from app.CAO.skills import (
    PlatformAdapterSkill,
    PublishCallbackSkill,
    PublishExecuteSkill,
    PublishHistorySkill,
    PublishPlanSkill,
    PublishRetryRecoverySkill,
)
from app.CEO.skills import CEOWorkflowSkill
from app.CFO.skills import ChargeSkill, EstimateCostSkill, VerifyBalanceSkill
from app.CIO.skills import CIOLogSkill, StoreSkill
from app.CTO.skills import PromptPackageSkill, PromptValidationSkill, PromptVersionSkill, TitleCandidateSkill
from app.CQO.skills import (
    ContentComplianceCheckSkill,
    DeliveryAssetCheckSkill,
    GeneAlignmentCheckSkill,
    QAReportSkill,
    RenderOutputCheckSkill,
    TechnicalSpecCheckSkill,
    VideoQualityCheckSkill,
)
from app.Production.skills import (
    AssetStorageSkill,
    ProductionRetryRecoverySkill,
    RenderExecuteSkill,
    ScriptDraftSkill,
    ScriptReviewSkill,
    SubtitleComposeSkill,
    VideoComposePlanSkill,
    VideoProcessSkill,
    VideoReviewSkill,
    VideoTaskSkill,
    VoiceoverGenerateSkill,
)
from app.Research.skills import (
    DomainQueryExpansionSkill,
    HotspotCollectionSkill,
    HotspotDedupSkill,
    HotspotRankingSkill,
    HotspotSnapshotSkill,
    MaterialSearchSkill,
)
from app.services.analysis import AIAnalysisService
from app.services.ceo_control_plane import control_plane
from app.services.finance import FinanceService
from app.services.hotspot import HotspotService
from app.services.publish import PublishService
from app.services.script import ScriptService
from app.services.trend_intelligence import TrendIntelligenceService
from app.services.video import VideoService
from app.services.workflow_runs import WorkflowRunService
from app.services.workflow_steps import WorkflowStepLogService
from app.skills.catalog import ensure_builtin_skills_registered
from app.skills.log.workflow_log import LogWorkflowSkill
from app.skills.runtime import SkillRuntimeManager


class WorkflowAssembly:
    """Builds the concrete service and skill graph needed by the execution engine."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.control_plane = control_plane
        self.hotspot_service = HotspotService(session)
        self.analysis_service = AIAnalysisService(session)
        self.script_service = ScriptService(session)
        self.video_service = VideoService(session)
        self.publish_service = PublishService(session)
        self.trend_service = TrendIntelligenceService()
        self.finance_service = FinanceService(session)
        self.workflow_run_service = WorkflowRunService(session)
        self.workflow_step_service = WorkflowStepLogService(session)
        self.skill_runtime = SkillRuntimeManager()

        ensure_builtin_skills_registered()

        self.ceo_skill = CEOWorkflowSkill()
        self.log_skill = LogWorkflowSkill()
        self.cio_log_skill = CIOLogSkill(session)
        self.cio_store_skill = StoreSkill(session)
        self.cfo_estimate_skill = EstimateCostSkill()
        self.cfo_verify_skill = VerifyBalanceSkill()
        self.cfo_charge_skill = ChargeSkill(session)

        self.domain_query_skill = DomainQueryExpansionSkill()
        self.hotspot_collection_skill = HotspotCollectionSkill()
        self.hotspot_dedup_skill = HotspotDedupSkill()
        self.material_search_skill = MaterialSearchSkill()
        self.hotspot_ranking_skill = HotspotRankingSkill()
        self.hotspot_snapshot_skill = HotspotSnapshotSkill()

        self.hotspot_structure_skill = HotspotStructureSkill()
        self.hook_extraction_skill = HookExtractionSkill()
        self.emotion_curve_skill = EmotionCurveSkill()
        self.risk_extraction_skill = RiskExtractionSkill()
        self.reusable_element_skill = ReusableElementSkill()
        self.analysis_persist_skill = AnalysisPersistSkill()

        self.prompt_package_skill = PromptPackageSkill()
        self.title_candidate_skill = TitleCandidateSkill()
        self.prompt_validation_skill = PromptValidationSkill()
        self.prompt_version_skill = PromptVersionSkill()

        self.script_draft_skill = ScriptDraftSkill()
        self.script_review_skill = ScriptReviewSkill()
        self.subtitle_compose_skill = SubtitleComposeSkill()
        self.voiceover_generate_skill = VoiceoverGenerateSkill()
        self.video_task_skill = VideoTaskSkill()
        self.video_process_skill = VideoProcessSkill()
        self.video_review_skill = VideoReviewSkill()
        self.video_compose_plan_skill = VideoComposePlanSkill()
        self.render_execute_skill = RenderExecuteSkill()
        self.asset_storage_skill = AssetStorageSkill()
        self.production_retry_skill = ProductionRetryRecoverySkill()

        self.video_quality_check_skill = VideoQualityCheckSkill()
        self.content_compliance_check_skill = ContentComplianceCheckSkill()
        self.delivery_asset_check_skill = DeliveryAssetCheckSkill()
        self.gene_alignment_check_skill = GeneAlignmentCheckSkill()
        self.render_output_check_skill = RenderOutputCheckSkill()
        self.technical_spec_check_skill = TechnicalSpecCheckSkill()
        self.qa_report_skill = QAReportSkill()

        self.publish_plan_skill = PublishPlanSkill()
        self.platform_adapter_skill = PlatformAdapterSkill()
        self.publish_execute_skill = PublishExecuteSkill()
        self.publish_callback_skill = PublishCallbackSkill()
        self.publish_history_skill = PublishHistorySkill()
        self.publish_retry_skill = PublishRetryRecoverySkill()

    async def load_hotspot(self, hotspot_id: str) -> HotspotItem:
        from sqlalchemy import select

        result = await self.session.execute(select(HotspotItem).where(HotspotItem.uuid == hotspot_id))
        hotspot = result.scalar_one_or_none()
        if not hotspot:
            raise ValueError(f"Hotspot {hotspot_id} not found")
        return hotspot

    def load_hotspot_sync(self, hotspot_data: dict[str, Any]) -> HotspotItem:
        return HotspotItem(
            uuid=hotspot_data["uuid"],
            platform=hotspot_data["platform"],
            content_id=hotspot_data["content_id"],
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

    def serialize_video_task(self, task: Any) -> dict[str, Any]:
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
