from __future__ import annotations

from copy import deepcopy
from typing import Any


LEADER_ORG_PROFILES: dict[str, dict[str, Any]] = {
    "lead.cfo": {
        "title_code": "CFO",
        "executive_title": "CFO 首席财务官",
        "department_name": "财务闸门中心",
        "display_name": "CFO 首席财务官 / 财务闸门中心",
        "role_level": "executive",
        "title_status": "active",
        "org_domain": "finance",
        "description": "负责预估成本、验资放行和扣款留痕，是生产流水线启动前的财务守门人。",
        "aliases": ["cfo", "finance", "chief financial officer", "财务", "首席财务官", "财务闸门"],
    },
    "lead.cio": {
        "title_code": "CIO",
        "executive_title": "CIO 首席信息官",
        "department_name": "信息中枢",
        "display_name": "CIO 首席信息官 / 信息中枢",
        "role_level": "executive",
        "title_status": "active",
        "org_domain": "information",
        "description": "负责仓库、日志、知识资产、测试稳定性与统一信息查询，是系统运行的信息底座。",
        "aliases": ["cio", "information", "chief information officer", "信息", "首席信息官", "日志", "仓库", "知识库"],
    },
    "lead.cho": {
        "title_code": "CHO",
        "executive_title": "CHO 首席人力官",
        "department_name": "公共 Agent 管理中心",
        "display_name": "CHO 首席人力官 / 公共 Agent 管理中心",
        "role_level": "executive",
        "title_status": "active",
        "org_domain": "human_operations",
        "description": "负责公共 Agent 编制、共享能力目录和通用代理健康状态，作为 CEO 直辖的公共 Agent 管理部门。",
        "aliases": ["cho", "chief human officer", "human", "公共agent", "公共 agent", "shared agent", "agent 管理"],
    },
    "lead.research": {
        "title_code": "RESEARCH",
        "executive_title": "Research Lead 调研负责人",
        "department_name": "热点调研中心",
        "display_name": "Research Lead 调研负责人 / 热点调研中心",
        "role_level": "department_lead",
        "title_status": "active",
        "org_domain": "research",
        "description": "负责发现热点、扩展搜索域、规划素材方向并维护候选池。",
        "aliases": ["research", "调研", "调研组", "调研负责人", "热点调研中心"],
    },
    "lead.analysis": {
        "title_code": "ANALYSIS",
        "executive_title": "Analysis Lead 分析负责人",
        "department_name": "内容分析中心",
        "display_name": "Analysis Lead 分析负责人 / 内容分析中心",
        "role_level": "department_lead",
        "title_status": "active",
        "org_domain": "analysis",
        "description": "负责拆解爆款结构、钩子、情绪曲线与风险信号，沉淀可复用分析资产。",
        "aliases": ["analysis", "分析", "分析组", "分析负责人", "内容分析中心"],
    },
    "lead.research_development": {
        "title_code": "CTO",
        "executive_title": "CTO 首席技术官",
        "department_name": "技术策划中心",
        "display_name": "CTO 首席技术官 / 技术策划中心",
        "role_level": "executive",
        "title_status": "active",
        "org_domain": "technology",
        "description": "负责提示词体系、标题方案、技术策划和生产前校验，是生产流水线的技术设计中枢。",
        "aliases": ["cto", "chief technology officer", "技术", "首席技术官", "策划", "planning", "research_development"],
    },
    "lead.production": {
        "title_code": "PRODUCTION",
        "executive_title": "Production Lead 制作负责人",
        "department_name": "生产执行中心",
        "display_name": "Production Lead 制作负责人 / 生产执行中心",
        "role_level": "department_lead",
        "title_status": "active",
        "org_domain": "production",
        "description": "负责脚本、字幕、配音、视频生成、合成渲染与产物落盘。",
        "aliases": ["production", "制作", "制作组", "制作负责人", "生产执行中心"],
    },
    "lead.qa": {
        "title_code": "CQO",
        "executive_title": "CQO 首席质量官",
        "department_name": "质量治理中心",
        "display_name": "CQO 首席质量官 / 质量治理中心",
        "role_level": "executive",
        "title_status": "active",
        "org_domain": "quality",
        "description": "负责画面、内容、爆款基因和技术参数质检，是生产流水线最关键的质量门禁。",
        "aliases": ["cqo", "chief quality officer", "qa", "quality", "质检", "质量", "首席质量官"],
    },
    "lead.publish": {
        "title_code": "CAO",
        "executive_title": "CAO 首席行政官",
        "department_name": "外部接口与交付中心",
        "display_name": "CAO 首席行政官 / 外部接口与交付中心",
        "role_level": "executive",
        "title_status": "interim_assignment",
        "org_domain": "administration",
        "description": "负责外部 API 接口、平台适配、交付执行、回执与记录闭环，当前由发布部门承接 CAO 职能。",
        "aliases": ["cao", "chief administrative officer", "行政", "首席行政官", "发布", "external api", "api", "外部接口", "publish"],
    },
    "lead.promotion": {
        "title_code": "CMO",
        "executive_title": "CMO 首席市场官",
        "department_name": "宣传与用户接口中心",
        "display_name": "CMO 首席市场官 / 宣传与用户接口中心",
        "role_level": "executive",
        "title_status": "active",
        "org_domain": "market",
        "description": "负责用户沟通、进度播报、报告包装与对外表达，是 CEO 直辖的唯一用户接口部门。",
        "aliases": ["cmo", "chief marketing officer", "promotion", "宣传", "市场", "首席市场官", "用户接口", "ui", "pr"],
    },
}


ORG_TITLE_REGISTRY: dict[str, list[dict[str, Any]]] = {
    "active_titles": [
        {
            "leader_name": leader_name,
            "title_code": profile["title_code"],
            "executive_title": profile["executive_title"],
            "department_name": profile["department_name"],
            "title_status": profile["title_status"],
            "role_level": profile["role_level"],
        }
        for leader_name, profile in LEADER_ORG_PROFILES.items()
        if profile.get("role_level") == "executive"
    ],
    "planned_titles": [
        {
            "title_code": "COO",
            "executive_title": "COO 首席运营官",
            "suggested_target": "lead.production",
            "status": "planned",
            "note": "后续可将生产执行中心进一步升级为 COO 级运营部门。",
        },
        {
            "title_code": "CSO",
            "executive_title": "CSO 首席战略官",
            "suggested_target": "lead.analysis",
            "status": "planned",
            "note": "后续可将内容分析中心进一步升级为战略分析岗位。",
        },
    ],
}


LEADER_STAGE_LABELS_CN: dict[str, str] = {
    leader_name: str(profile["display_name"]) for leader_name, profile in LEADER_ORG_PROFILES.items()
}
LEADER_STAGE_LABELS_CN["ceo.workflow"] = "CEO 调度"


LEADER_STAGE_LABELS_EN: dict[str, str] = {
    "lead.cfo": "CFO Finance Gate",
    "lead.cio": "CIO Information Hub",
    "lead.cho": "CHO Public Agent Center",
    "lead.research": "Research Lead",
    "lead.analysis": "Analysis Lead",
    "lead.research_development": "CTO Technology Planning",
    "lead.production": "Production Lead",
    "lead.qa": "CQO Quality Center",
    "lead.publish": "CAO External API Center",
    "lead.promotion": "CMO User Communication Center",
    "ceo.workflow": "CEO Orchestration",
}


LEADER_QUERY_ALIASES: dict[str, tuple[str, ...]] = {
    leader_name: tuple(str(alias) for alias in profile.get("aliases") or [])
    for leader_name, profile in LEADER_ORG_PROFILES.items()
}


def apply_org_naming_defaults(leader_name: str, config: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(config)
    profile = deepcopy(LEADER_ORG_PROFILES.get(leader_name) or {})
    if not profile:
        return merged

    merged["display_name"] = str(profile["display_name"])
    merged["description"] = str(profile["description"])

    aliases: list[str] = []
    for alias in [*(merged.get("aliases") or []), *(profile.get("aliases") or [])]:
        normalized = str(alias or "").strip()
        if normalized and normalized not in aliases:
            aliases.append(normalized)
    merged["aliases"] = aliases

    tags: list[str] = []
    for tag in [*(merged.get("tags") or []), str(profile.get("org_domain") or ""), str(profile.get("title_code") or "").lower()]:
        normalized = str(tag or "").strip()
        if normalized and normalized not in tags:
            tags.append(normalized)
    merged["tags"] = tags
    merged["organization_profile"] = profile
    return merged


def build_org_title_registry() -> dict[str, list[dict[str, Any]]]:
    return deepcopy(ORG_TITLE_REGISTRY)
