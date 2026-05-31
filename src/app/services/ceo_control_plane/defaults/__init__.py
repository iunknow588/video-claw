from __future__ import annotations

from typing import Any

from app.leaders.organization import apply_org_naming_defaults


CONTROL_PLANE_MISSION = (
    "CEO's mission is to organize and evolve the company: govern CFO, CIO, CHO, "
    "CMO, CAO, and the production leaders while keeping the workflow observable, "
    "orderly, and continuously improvable."
)
CONTROL_PLANE_SCOPE = "company_system"


def _leader(
    *,
    display_name: str,
    description: str,
    model: str,
    bound_tools: list[str],
    aliases: list[str],
    tags: list[str],
    token_limit: int,
    parallelism: int = 1,
    model_quota: str = "standard",
) -> dict[str, Any]:
    return {
        "display_name": display_name,
        "description": description,
        "model": model,
        "bound_tools": bound_tools,
        "aliases": aliases,
        "tags": tags,
        "token_limit": token_limit,
        "resource_allocations": {
            "model_quota": model_quota,
            "parallelism": parallelism,
        },
    }


DEFAULT_LEADERS: dict[str, dict[str, Any]] = {
    "lead.cfo": _leader(
        display_name="CFO Finance Gate",
        description="Estimate budget, verify balance, charge usage, and decide whether a request can enter production.",
        model="deepseek-v4",
        bound_tools=[
            "lead.cfo.estimate_cost",
            "lead.cfo.verify_balance",
            "lead.cfo.charge",
        ],
        aliases=["cfo", "finance", "finance_gate"],
        tags=["finance", "gate"],
        token_limit=6000,
    ),
    "lead.cio": _leader(
        display_name="CIO Information Hub",
        description="Owns storage, logs, knowledge assets, testing stability, and company-wide information queries.",
        model="deepseek-v4",
        bound_tools=[
            "lead.cio.store",
            "lead.cio.retrieve",
            "lead.cio.log",
            "lead.cio.query_log",
            "lead.cio.knowledge_base",
        ],
        aliases=["cio", "information", "repository", "log", "knowledge"],
        tags=["information", "repository", "observability"],
        token_limit=8000,
    ),
    "lead.cho": _leader(
        display_name="CHO Public Agent Center",
        description="Owns shared-agent roster, capability governance, and public agent health visibility.",
        model="deepseek-v4",
        bound_tools=[
            "lead.cho.public_agent_registry",
            "lead.cho.agent_capability",
            "lead.cho.shared_agent_health",
        ],
        aliases=["cho", "human", "shared_agent", "public_agent", "common_agent"],
        tags=["human_operations", "agent", "shared"],
        token_limit=6000,
    ),
    "lead.research": _leader(
        display_name="Research Center",
        description="Discover hotspots, expand search directions, and maintain the candidate pool.",
        model="deepseek-v4",
        bound_tools=[
            "lead.research.domain_query_expansion",
            "lead.research.hotspot_collection",
            "lead.research.hotspot_dedup",
            "lead.research.hotspot_ranking",
            "lead.research.hotspot_snapshot",
            "lead.research.material_search",
        ],
        aliases=["research", "discovery"],
        tags=["research", "discovery"],
        token_limit=12000,
    ),
    "lead.analysis": _leader(
        display_name="Analysis Center",
        description="Break down structure, hooks, emotional rhythm, and reusable content patterns.",
        model="deepseek-v4",
        bound_tools=[
            "lead.analysis.hotspot_structure",
            "lead.analysis.hook_extraction",
            "lead.analysis.emotion_curve",
            "lead.analysis.risk_extraction",
            "lead.analysis.reusable_element",
            "lead.analysis.analysis_persist",
        ],
        aliases=["analysis", "insight"],
        tags=["analysis", "insight"],
        token_limit=14000,
    ),
    "lead.research_development": _leader(
        display_name="CTO Technology Planning",
        description="Owns prompt packages, title options, validation, and prompt version governance.",
        model="glm-5.1",
        bound_tools=[
            "lead.research_development.prompt_package",
            "lead.research_development.title_candidate",
            "lead.research_development.prompt_validation",
            "lead.research_development.prompt_version",
        ],
        aliases=["cto", "planning", "research_development"],
        tags=["planning", "prompt"],
        token_limit=16000,
        model_quota="priority",
    ),
    "lead.production": _leader(
        display_name="Production Execution Center",
        description="Owns script drafting, subtitle and voice generation, video composition, rendering, and asset landing.",
        model="glm-5.1",
        bound_tools=[
            "lead.production.script_draft",
            "lead.production.script_review",
            "lead.production.subtitle_compose",
            "lead.production.voiceover_generate",
            "lead.production.video_task",
            "lead.production.video_process",
            "lead.production.video_review",
            "lead.production.video_compose_plan",
            "lead.production.render_execute",
            "lead.production.asset_storage",
            "lead.production.retry_recovery",
        ],
        aliases=["production", "delivery"],
        tags=["production", "delivery"],
        token_limit=18000,
        model_quota="priority",
    ),
    "lead.qa": _leader(
        display_name="CQO Quality Gate",
        description="Runs the formal quality gate, emits QA reports, and routes failed work back for rework.",
        model="glm-5.1",
        bound_tools=[
            "lead.qa.video_quality_check",
            "lead.qa.content_compliance_check",
            "lead.qa.gene_alignment_check",
            "lead.qa.technical_spec_check",
            "lead.qa.delivery_asset_check",
            "lead.qa.render_output_check",
            "lead.qa.qa_report",
        ],
        aliases=["qa", "quality", "quality_gate"],
        tags=["qa", "gate"],
        token_limit=12000,
    ),
    "lead.publish": _leader(
        display_name="CAO External API Center",
        description="Owns platform adaptation, publish execution, callbacks, and external delivery closure.",
        model="deepseek-v4",
        bound_tools=[
            "lead.publish.publish_plan",
            "lead.publish.platform_adapter",
            "lead.publish.publish_execute",
            "lead.publish.publish_callback",
            "lead.publish.publish_history",
            "lead.publish.retry_recovery",
        ],
        aliases=["publish", "api", "external_api", "external_interface", "platform_interface"],
        tags=["publish", "platform", "external_api"],
        token_limit=10000,
    ),
    "lead.promotion": _leader(
        display_name="CMO Promotion Interface",
        description="Owns user-facing communication, progress broadcasting, and report packaging under CEO governance.",
        model="deepseek-v4",
        bound_tools=[
            "lead.promotion.chat_ui",
            "lead.promotion.progress_ui",
            "lead.promotion.report_ui",
        ],
        aliases=["promotion", "ui", "pr", "xuanchuan", "xuanchuanbu"],
        tags=["promotion", "ui", "communication"],
        token_limit=6000,
    ),
}


for _leader_name in list(DEFAULT_LEADERS):
    DEFAULT_LEADERS[_leader_name] = apply_org_naming_defaults(_leader_name, DEFAULT_LEADERS[_leader_name])


DEFAULT_WORKFLOW: dict[str, Any] = {
    "version": 1,
    "dispatch_mode": "graph",
    "main_route": [
        "lead.cfo",
        "lead.research",
        "lead.analysis",
        "lead.research_development",
        "lead.production",
        "lead.qa",
        "lead.publish",
    ],
    "edges": [
        {"from": "lead.cfo", "to": "lead.research"},
        {"from": "lead.research", "to": "lead.analysis"},
        {"from": "lead.analysis", "to": "lead.research_development"},
        {"from": "lead.research_development", "to": "lead.production"},
        {"from": "lead.production", "to": "lead.qa"},
    ],
    "conditional_edges": [
        {
            "from": "lead.qa",
            "router_func": "qa_gate",
            "mapping": {
                "passed": "lead.publish",
                "retry_production": "lead.production",
                "retry_research_development": "lead.research_development",
            },
        }
    ],
    "parallel_groups": [],
}
