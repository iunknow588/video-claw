from __future__ import annotations

from typing import Any

from app.CAO.skills import (
    PlatformAdapterSkill,
    PublishCallbackSkill,
    PublishExecuteSkill,
    PublishHistorySkill,
    PublishPlanSkill,
    PublishRetryRecoverySkill,
)
from app.CHO.skills import AgentCapabilitySkill, PublicAgentRegistrySkill, SharedAgentHealthSkill
from app.CEO.skills import CEOWorkflowSkill
from app.CFO.skills import ChargeSkill, EstimateCostSkill, VerifyBalanceSkill
from app.CIO.skills import CIOLogSkill, KnowledgeBaseSkill, QueryLogSkill, RetrieveSkill, StoreSkill
from app.CMO.skills import ChatUISkill, ProgressUISkill, ReportUISkill
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
from app.Analysis.skills import (
    AnalysisPersistSkill,
    EmotionCurveSkill,
    HookExtractionSkill,
    HotspotStructureSkill,
    ReusableElementSkill,
    RiskExtractionSkill,
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
from app.skills.log.workflow_log import LogWorkflowSkill
from app.skills.registry import registry

BUILTIN_SKILL_FACTORIES = (
    CEOWorkflowSkill,
    LogWorkflowSkill,
    EstimateCostSkill,
    VerifyBalanceSkill,
    ChargeSkill,
    StoreSkill,
    RetrieveSkill,
    CIOLogSkill,
    QueryLogSkill,
    KnowledgeBaseSkill,
    PublicAgentRegistrySkill,
    AgentCapabilitySkill,
    SharedAgentHealthSkill,
    DomainQueryExpansionSkill,
    HotspotCollectionSkill,
    HotspotDedupSkill,
    MaterialSearchSkill,
    HotspotRankingSkill,
    HotspotSnapshotSkill,
    HotspotStructureSkill,
    HookExtractionSkill,
    EmotionCurveSkill,
    RiskExtractionSkill,
    ReusableElementSkill,
    AnalysisPersistSkill,
    ChatUISkill,
    ProgressUISkill,
    ReportUISkill,
    VideoQualityCheckSkill,
    ContentComplianceCheckSkill,
    DeliveryAssetCheckSkill,
    GeneAlignmentCheckSkill,
    RenderOutputCheckSkill,
    TechnicalSpecCheckSkill,
    QAReportSkill,
    PromptPackageSkill,
    TitleCandidateSkill,
    PromptValidationSkill,
    PromptVersionSkill,
    ScriptDraftSkill,
    ScriptReviewSkill,
    SubtitleComposeSkill,
    VoiceoverGenerateSkill,
    VideoTaskSkill,
    VideoProcessSkill,
    VideoReviewSkill,
    VideoComposePlanSkill,
    RenderExecuteSkill,
    AssetStorageSkill,
    ProductionRetryRecoverySkill,
    PublishPlanSkill,
    PlatformAdapterSkill,
    PublishExecuteSkill,
    PublishCallbackSkill,
    PublishHistorySkill,
    PublishRetryRecoverySkill,
)

SKILL_METADATA_OVERRIDES: dict[str, dict[str, Any]] = {
    "ceo.workflow": {
        "description": "CEO control plane for company governance: CHO public-agent governance, CMO user communication, CFO, CIO, CAO external interfaces, and production-leader lifecycle, workflow ordering, monitoring, optimization commands, resource allocation, and evolution control.",
        "tags": ["ceo", "workflow", "governance", "planning", "evolution"],
        "parameters_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "platform": {"type": "string"},
                "trace_id": {"type": "string"},
                "name": {"type": "string"},
                "config": {"type": "object"},
                "graph_definition": {"type": "object"},
                "from_leader": {"type": "string"},
                "to_leader": {"type": "string"},
                "router_func": {"type": "string"},
                "mapping": {"type": "object"},
                "leader_name": {"type": "string"},
                "target_metric": {"type": "string"},
                "goal_value": {},
                "proposal": {"type": "object"},
                "token_limit": {"type": "integer"},
                "resource_type": {"type": "string"},
                "amount": {},
                "version": {"type": "integer"},
                "company_status": {"type": "object"},
                "task_progress": {"type": "object"},
            },
            "required": [],
        },
        "dependencies": [
            "lead.promotion",
            "lead.cho",
            "lead.cfo.estimate_cost",
            "lead.cfo.verify_balance",
            "lead.cfo.charge",
            "lead.cio.log",
            "lead.cio.store",
            "lead.research",
            "lead.analysis",
            "lead.research_development",
            "lead.production",
            "lead.qa",
            "lead.publish",
        ],
    },
    "log.workflow": {
        "description": "Legacy workflow logger kept as a compatibility alias under the upgraded CIO observability domain.",
        "tags": ["log", "workflow", "observability", "legacy"],
    },
    "lead.cfo.estimate_cost": {
        "description": "Estimates token usage, provider mix, and expected spend before the production system starts.",
        "tags": ["lead", "cfo", "finance", "gate"],
    },
    "lead.cfo.verify_balance": {
        "description": "Verifies provider readiness and remaining budget before CFO releases a task into production.",
        "tags": ["lead", "cfo", "finance", "gate"],
    },
    "lead.cfo.charge": {
        "description": "Records a CFO precharge receipt and returns the finance transaction voucher for the run.",
        "tags": ["lead", "cfo", "finance", "gate"],
    },
    "lead.cio.store": {
        "description": "Stores workflow bundles in the CIO lightweight repository.",
        "tags": ["lead", "cio", "storage", "repository"],
    },
    "lead.cio.retrieve": {
        "description": "Retrieves stored workflow bundles from the CIO repository.",
        "tags": ["lead", "cio", "storage", "repository"],
    },
    "lead.cio.log": {
        "description": "Records CIO-owned information events and information-infrastructure annotations.",
        "tags": ["lead", "cio", "log", "observability"],
    },
    "lead.cio.query_log": {
        "description": "Queries historical workflow logs through the CIO information interface.",
        "tags": ["lead", "cio", "log", "query"],
    },
    "lead.cio.knowledge_base": {
        "description": "Maintains templates, platform guides, and viral-case notes in the CIO knowledge base.",
        "tags": ["lead", "cio", "knowledge", "repository"],
    },
    "lead.cho.public_agent_registry": {
        "description": "Maintains the CHO roster of shared and public agent entrypoints under CEO governance.",
        "tags": ["lead", "cho", "agent", "registry"],
    },
    "lead.cho.agent_capability": {
        "description": "Describes capability scope and ownership for CHO-managed public agents.",
        "tags": ["lead", "cho", "agent", "capability"],
        "dependencies": ["lead.cho.public_agent_registry"],
    },
    "lead.cho.shared_agent_health": {
        "description": "Reports availability and governance health for shared agents managed by CHO.",
        "tags": ["lead", "cho", "agent", "health"],
        "dependencies": ["lead.cho.public_agent_registry", "lead.cio.log"],
    },
    "lead.research.domain_query_expansion": {
        "description": "Expands a content domain into platform-ready discovery queries.",
        "tags": ["lead", "research", "query"],
        "parameters_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "audience": {"type": "string"},
                "publish_goal": {"type": "string"},
                "trace_id": {"type": "string"},
            },
            "required": ["domain"],
        },
    },
    "lead.research.hotspot_collection": {"description": "Normalizes raw hotspot candidates into a research bundle."},
    "lead.research.hotspot_dedup": {"description": "Deduplicates collected hotspot candidates."},
    "lead.research.material_search": {
        "description": "Builds material-search candidates, scene mappings, and cache keys inspired by stock-video acquisition workflows.",
        "tags": ["lead", "research", "material", "planning"],
    },
    "lead.research.hotspot_ranking": {"description": "Ranks hotspot candidates by heat and relevance."},
    "lead.research.hotspot_snapshot": {"description": "Captures the selected hotspot snapshot for the current trace."},
    "lead.analysis.hotspot_structure": {"description": "Extracts the structural pattern from an analysis report."},
    "lead.analysis.hook_extraction": {"description": "Derives reusable hook patterns from structured analysis output."},
    "lead.analysis.emotion_curve": {"description": "Maps emotional pacing cues from the current analysis bundle."},
    "lead.analysis.risk_extraction": {"description": "Extracts editorial, copyright, and compliance risks."},
    "lead.analysis.reusable_element": {"description": "Identifies reusable creative elements for future scripts."},
    "lead.analysis.analysis_persist": {"description": "Packages analysis artifacts into a persisted trace bundle."},
    "lead.promotion.chat_ui": {
        "description": "Receives user messages and turns them into promotion-side task directives or production-governance queries.",
        "tags": ["lead", "promotion", "ui", "chat"],
        "parameters_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["action"],
        },
        "dependencies": [],
    },
    "lead.promotion.progress_ui": {
        "description": "Formats internal workflow stage updates for the external UI channel.",
        "tags": ["lead", "promotion", "ui", "progress"],
        "parameters_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "event": {"type": "object"},
            },
            "required": ["action", "event"],
        },
        "dependencies": [
            "lead.cfo.estimate_cost",
            "lead.research",
            "lead.analysis",
            "lead.production",
            "lead.qa",
            "lead.publish",
        ],
    },
    "lead.promotion.report_ui": {
        "description": "Packages production workflow results, governance snapshots, and trace reports into UI-ready payloads.",
        "tags": ["lead", "promotion", "ui", "report"],
        "parameters_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "runs": {"type": "array"},
                "run": {"type": "object"},
                "summary": {"type": "object"},
                "result": {"type": "object"},
                "message": {"type": "string"},
            },
            "required": ["action"],
        },
        "dependencies": ["lead.cfo.charge", "lead.cio.query_log", "lead.qa", "lead.publish"],
    },
    "lead.qa.video_quality_check": {
        "description": "Checks whether a generated video is complete and visually publishable.",
        "tags": ["lead", "qa", "video"],
        "parameters_schema": {
            "type": "object",
            "properties": {
                "video_task": {"type": ["object", "null"]},
                "platform": {"type": "string"},
            },
            "required": ["platform"],
        },
        "dependencies": ["lead.production.video_task", "lead.production.video_process"],
    },
    "lead.qa.content_compliance_check": {
        "description": "Checks scripts and video payloads for sensitive content and platform safety issues.",
        "tags": ["lead", "qa", "compliance"],
        "parameters_schema": {
            "type": "object",
            "properties": {
                "script": {"type": "object"},
                "video_task": {"type": ["object", "null"]},
                "platform": {"type": "string"},
            },
            "required": ["script", "platform"],
        },
        "dependencies": ["lead.analysis.risk_extraction", "lead.production.script_review"],
    },
    "lead.qa.delivery_asset_check": {
        "description": "Checks whether subtitles, narration, material mapping, and composition inputs are fully assembled.",
        "tags": ["lead", "qa", "delivery", "asset"],
    },
    "lead.qa.render_output_check": {
        "description": "Checks whether the final render output and render manifest are present and usable.",
        "tags": ["lead", "qa", "render", "output"],
    },
    "lead.qa.gene_alignment_check": {
        "description": "Measures whether the produced script still matches the analyzed viral-content DNA.",
        "tags": ["lead", "qa", "alignment"],
        "parameters_schema": {
            "type": "object",
            "properties": {
                "script": {"type": "object"},
                "analysis_bundle": {"type": "object"},
                "prompt_bundle": {"type": "object"},
            },
            "required": ["script", "analysis_bundle"],
        },
        "dependencies": ["lead.analysis.hook_extraction", "lead.analysis.emotion_curve", "lead.research_development.prompt_package"],
    },
    "lead.qa.technical_spec_check": {
        "description": "Checks duration, resolution, and platform-format constraints before publish.",
        "tags": ["lead", "qa", "technical"],
        "parameters_schema": {
            "type": "object",
            "properties": {
                "platform": {"type": "string"},
                "script": {"type": "object"},
                "video_task": {"type": ["object", "null"]},
            },
            "required": ["platform", "script"],
        },
        "dependencies": ["lead.production.video_task", "lead.publish.platform_adapter"],
    },
    "lead.qa.qa_report": {
        "description": "Aggregates QA checks into a final quality-gate decision and reroute target.",
        "tags": ["lead", "qa", "report"],
        "parameters_schema": {
            "type": "object",
            "properties": {
                "checks": {"type": "array"},
                "video_task": {"type": ["object", "null"]},
            },
            "required": ["checks"],
        },
        "dependencies": [
            "lead.qa.video_quality_check",
            "lead.qa.content_compliance_check",
            "lead.qa.gene_alignment_check",
            "lead.qa.technical_spec_check",
        ],
    },
    "lead.research_development.prompt_package": {"description": "Shapes the prompt package for downstream script work."},
    "lead.research_development.title_candidate": {"description": "Generates candidate titles from the prompt package."},
    "lead.research_development.prompt_validation": {"description": "Validates prompt and title consistency before production."},
    "lead.research_development.prompt_version": {"description": "Versions the validated prompt bundle."},
    "lead.production.script_draft": {"description": "Wraps a generated script into the managed production skill format."},
    "lead.production.script_review": {"description": "Wraps an approved script into the production trace output."},
    "lead.production.subtitle_compose": {
        "description": "Generates an SRT subtitle asset from the production script for downstream packaging and review.",
        "tags": ["lead", "production", "subtitle"],
    },
    "lead.production.voiceover_generate": {
        "description": "Generates a lightweight narration asset and SSML-ready voice plan from the production script.",
        "tags": ["lead", "production", "voiceover"],
    },
    "lead.production.video_task": {"description": "Packages the generated video task for managed tracking."},
    "lead.production.video_process": {"description": "Packages processed video task output for review."},
    "lead.production.video_review": {"description": "Packages reviewed video output for storage handoff."},
    "lead.production.video_compose_plan": {
        "description": "Builds an ffmpeg-friendly composition plan combining materials, narration, subtitles, and render preset.",
        "tags": ["lead", "production", "compose"],
    },
    "lead.production.render_execute": {
        "description": "Builds a delivery-facing render artifact or preview asset from the composition plan.",
        "tags": ["lead", "production", "render"],
    },
    "lead.production.asset_storage": {"description": "Finalizes storage-facing asset metadata for a generated video."},
    "lead.production.retry_recovery": {"description": "Signals whether production should request a retry."},
    "lead.publish.publish_plan": {
        "description": "Builds the external API handoff plan from the production result.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "platform": {"type": "string"},
                "publish_goal": {"type": "string"},
                "audience": {"type": "string"},
                "video_url": {"type": "string"},
                "video_task_id": {"type": "string"},
                "trace_id": {"type": "string"},
            },
            "required": ["platform"],
        },
    },
    "lead.publish.platform_adapter": {"description": "Adapts an external API handoff plan into platform-specific payload fields."},
    "lead.publish.publish_execute": {"description": "Normalizes external API execution results into a managed bundle."},
    "lead.publish.publish_callback": {"description": "Captures external API callback status for the current trace."},
    "lead.publish.publish_history": {"description": "Captures external API delivery history records for the current trace."},
    "lead.publish.retry_recovery": {"description": "Signals whether the external API gateway should request a retry."},
}


def iter_builtin_skill_instances() -> list[object]:
    return [factory() for factory in BUILTIN_SKILL_FACTORIES]


def ensure_builtin_skills_registered() -> None:
    for instance in iter_builtin_skill_instances():
        skill_name = getattr(instance, "skill_name", None) or getattr(instance, "name", None)
        registry.register_instance(instance, overrides=SKILL_METADATA_OVERRIDES.get(skill_name or "", {}))
