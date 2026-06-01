from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from departments.CEO.leaders.base import ManagedLeader


class DepartmentLeader(ManagedLeader):
    department_type = ""
    focus_metrics: list[str] = []
    managed_capabilities: list[str] = []
    routing_note = ""
    periodic_report_message = ""
    periodic_summary_key = ""
    periodic_summary_context = ""

    def build_report(self) -> dict[str, Any]:
        report = super().build_report()
        report["department_type"] = self.department_type
        report["focus_metrics"] = list(self.focus_metrics)
        report["managed_capabilities"] = list(self.managed_capabilities)
        return report

    def accept_command(self, *, command_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = super().accept_command(command_type=command_type, payload=payload)
        if self.routing_note:
            event["routing_note"] = self.routing_note
        return event

    def build_periodic_report(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        report = super().build_periodic_report(context)
        if self.periodic_summary_key and self.periodic_summary_context:
            report[self.periodic_summary_key] = dict((context or {}).get(self.periodic_summary_context) or {})
        if self.periodic_report_message:
            report["report_message"] = self.periodic_report_message
        return report


class FinanceLeader(DepartmentLeader):
    department_type = "finance_gate"
    focus_metrics = ["budget_guardrail", "estimated_cost", "provider_readiness"]
    managed_capabilities = ["estimate", "verify_balance", "charge"]
    routing_note = "CFO will translate governance commands into budget, quota, or gate-threshold changes."
    periodic_report_message = "CFO 定期向 CEO 汇报预算、预留成本和闸门放行情况。"
    periodic_summary_key = "finance_summary"
    periodic_summary_context = "finance_metrics"


class InformationLeader(DepartmentLeader):
    department_type = "information_hub"
    focus_metrics = ["artifact_count", "log_record_count", "knowledge_asset_count"]
    managed_capabilities = ["store", "retrieve", "log", "query_log", "knowledge_base"]

    def propose_change(self, proposal: dict[str, Any]) -> dict[str, Any]:
        normalized = {
            **deepcopy(proposal),
            "requires_data_migration": bool(proposal.get("requires_data_migration", False)),
            "reviewed_at": datetime.now(UTC),
        }
        return super().propose_change(normalized)

    def build_periodic_report(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        report = super().build_periodic_report(context)
        information_metrics = dict((context or {}).get("information_metrics") or {})
        run_metrics = dict((context or {}).get("run_metrics") or {})
        quality_metrics = dict((context or {}).get("quality_metrics") or {})
        render_metrics = dict((context or {}).get("render_metrics") or {})
        report["focus_metrics"] = [
            "artifact_count",
            "log_record_count",
            "knowledge_asset_count",
            "workflow_success_rate",
            "qa_pass_rate",
            "render_success_rate",
        ]
        report["testing_and_stability"] = {
            "owner": "lead.cio",
            "testing_scope": ["api", "workflow", "storage", "observability", "render"],
            "workflow_success_rate": run_metrics.get("success_rate", 0.0),
            "qa_pass_rate": quality_metrics.get("qa_pass_rate", 0.0),
            "render_success_rate": render_metrics.get("render_success_rate", 0.0),
            "ffmpeg_preview_runs": render_metrics.get("ffmpeg_preview_runs", 0),
            "preview_placeholder_runs": render_metrics.get("preview_placeholder_runs", 0),
            "artifact_count": information_metrics.get("artifact_count", 0),
            "log_record_count": information_metrics.get("log_record_count", 0),
        }
        report["report_message"] = "CIO 定期向 CEO 汇报信息底座、测试治理和系统稳定性。"
        return report


class HumanOpsLeader(DepartmentLeader):
    department_type = "public_agent_management"
    focus_metrics = ["public_agent_count", "agent_availability", "shared_agent_change_count"]
    managed_capabilities = ["public_agent_registry", "agent_capability", "shared_agent_health"]
    periodic_report_message = "CHO 定期向 CEO 汇报公共 Agent 编制、可用性和共享能力变更。"


class ResearchLeader(DepartmentLeader):
    department_type = "CSO"
    focus_metrics = ["discovery_coverage", "hotspot_relevance", "dedup_efficiency"]
    periodic_report_message = "Research 定期向 CEO 汇报热点发现覆盖率与候选质量。"


class AnalysisLeader(DepartmentLeader):
    department_type = "CCO"
    focus_metrics = ["analysis_depth", "risk_detection", "reusable_signal_density"]
    periodic_report_message = "Analysis 定期向 CEO 汇报结构分析深度和风险识别表现。"


class PlanningLeader(DepartmentLeader):
    department_type = "planning"
    focus_metrics = ["prompt_quality", "title_hit_rate", "token_efficiency"]
    periodic_report_message = "CTO 定期向 CEO 汇报提示词质量、标题表现和 token 效率。"


class ProductionLeader(DepartmentLeader):
    department_type = "COO"
    focus_metrics = ["workflow_success_rate", "video_generation_rate", "rework_count"]
    routing_note = "Production will respond through prompt adjustments, script generation tuning, or retry policy changes."
    periodic_report_message = "Production 定期向 CEO 汇报成片产能、返工情况和执行稳定性。"


class QALeader(DepartmentLeader):
    department_type = "quality_gate"
    focus_metrics = ["qa_pass_rate", "false_block_rate", "reroute_accuracy"]
    routing_note = "QA will translate commands into threshold, weighting, or reroute-policy changes."
    periodic_report_message = "CQO 定期向 CEO 汇报质检通过率、门禁精度和返工导向。"
    periodic_summary_key = "quality_summary"
    periodic_summary_context = "quality_metrics"


class CAOLeader(DepartmentLeader):
    department_type = "external_api_gateway"
    focus_metrics = ["external_api_success_rate", "callback_reliability", "platform_fit"]
    managed_capabilities = [
        "publish_plan",
        "platform_adapter",
        "publish_execute",
        "publish_callback",
        "publish_history",
        "retry_recovery",
    ]
    periodic_report_message = "CAO 定期向 CEO 汇报外部接口可用性、平台回执和交付表现。"


class CMOLeader(DepartmentLeader):
    department_type = "promotion_interface"
    focus_metrics = ["response_clarity", "status_delivery_timeliness", "report_readability"]
    managed_capabilities = ["chat_ui", "progress_ui", "report_ui"]
    routing_note = (
        "CMO will translate governance commands into interaction policy, message clarity, and report-format changes."
    )
    periodic_report_message = "CMO 定期向 CEO 汇报用户沟通质量、进度传达及时性和报告呈现清晰度。"

    def build_periodic_report(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        report = super().build_periodic_report(context)
        report["interaction_scope"] = {
            "user_facing": True,
            "direct_ceo_chat": False,
            "managed_by_ceo": True,
            "in_main_workflow_route": False,
        }
        return report


PublishLeader = CAOLeader
PromotionLeader = CMOLeader


LEADER_CLASS_MAP: dict[str, type[ManagedLeader]] = {
    "lead.cfo": FinanceLeader,
    "lead.cio": InformationLeader,
    "lead.cho": HumanOpsLeader,
    "lead.promotion": CMOLeader,
    "lead.research": ResearchLeader,
    "lead.analysis": AnalysisLeader,
    "lead.research_development": PlanningLeader,
    "lead.production": ProductionLeader,
    "lead.qa": QALeader,
    "lead.publish": CAOLeader,
}


def build_department_leader(name: str, config: dict[str, Any]) -> ManagedLeader:
    leader_cls = LEADER_CLASS_MAP.get(name, ManagedLeader)
    leader = leader_cls(
        name=name,
        display_name=str(config.get("display_name") or name),
        description=str(config.get("description") or "未配置说明"),
        status=str(config.get("status") or "active"),
        version=int(config.get("version") or 1),
        model=config.get("model"),
        system_prompt=config.get("system_prompt"),
        bound_tools=list(config.get("bound_tools") or []),
        aliases=list(config.get("aliases") or []),
        tags=list(config.get("tags") or []),
        token_limit=int(config.get("token_limit") or 10000),
        resource_allocations=dict(config.get("resource_allocations") or {}),
        organization_profile=dict(config.get("organization_profile") or {}),
    )
    leader.resource_allocations.setdefault("token_limit", leader.token_limit)
    return leader
