from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


PUBLIC_STAGE_LABELS = {
    "lead.cfo": "财务闸门",
    "lead.research": "热点调研",
    "lead.analysis": "内容分析",
    "lead.planning": "技术策划",
    "lead.research_development": "技术策划",
    "lead.production": "生产执行",
    "lead.qa": "质量检查",
    "lead.publish": "对外交付",
}

STAGE_IDENTITY_KEYS = {
    "lead.cfo": "cfo",
    "lead.research": "cso",
    "lead.analysis": "cco",
    "lead.planning": "cto",
    "lead.research_development": "cto",
    "lead.production": "coo",
    "lead.qa": "cqo",
    "lead.publish": "cao",
}

STATUS_LABELS = {
    "running": "执行中",
    "success": "已完成",
    "failed": "失败",
}

RUNNING_MESSAGES = {
    "lead.cfo": "正在进行预算校验。",
    "lead.research": "正在扩展关键词并检索热点。",
    "lead.analysis": "正在拆解爆款结构与风险。",
    "lead.planning": "正在整理策划方案与提示词。",
    "lead.research_development": "正在整理策划方案与提示词。",
    "lead.production": "正在生成脚本与制作素材。",
    "lead.qa": "正在进行质量检查。",
    "lead.publish": "正在整理交付结果并准备对外回传。",
}

SUCCESS_MESSAGES = {
    "lead.cfo": "预算校验已通过，流程继续推进。",
    "lead.research": "热点检索已完成，已整理候选内容。",
    "lead.analysis": "爆款基因分析已完成。",
    "lead.planning": "提示词与策划包已生成。",
    "lead.research_development": "提示词与策划包已生成。",
    "lead.production": "脚本与制作素材已生成。",
    "lead.qa": "质量检查已完成。",
    "lead.publish": "交付结果已整理完成。",
}


def build_public_status_payload(stage: str, status: str, raw_message: Any = None) -> dict[str, str | None]:
    normalized_stage = str(stage or "").strip()
    normalized_status = str(status or "").strip().lower()
    raw_text = str(raw_message or "").strip()

    return {
        "actor_key": STAGE_IDENTITY_KEYS.get(normalized_stage),
        "stage_label": PUBLIC_STAGE_LABELS.get(normalized_stage, normalized_stage or "流程阶段"),
        "status_label": STATUS_LABELS.get(normalized_status, normalized_status or "已记录"),
        "message": _build_public_message(normalized_stage, normalized_status, raw_text),
        "raw_message": raw_text or None,
    }


def build_public_artifact_payload(
    *,
    stage: str,
    artifact_type: str,
    payload: dict[str, Any] | None,
    trace_id: str,
    workflow_run_id: str | None = None,
) -> dict[str, Any] | None:
    artifact = dict(payload or {})
    builder_map = {
        "finance_bundle": _build_finance_artifact,
        "research_bundle": _build_research_artifact,
        "analysis_bundle": _build_analysis_artifact,
        "planning_bundle": _build_planning_artifact,
        "production_bundle": _build_production_artifact,
        "qa_bundle": _build_qa_artifact,
        "publish_bundle": _build_publish_artifact,
    }
    builder = builder_map.get(artifact_type)
    if not builder:
        return None

    try:
        built = builder(stage=stage, payload=artifact)
    except Exception:
        return None
    if not built:
        return None

    built["type"] = "artifact"
    built["stage"] = stage
    built["actor_key"] = STAGE_IDENTITY_KEYS.get(stage)
    built["stage_label"] = PUBLIC_STAGE_LABELS.get(stage, stage or "流程阶段")
    built["trace_id"] = trace_id
    built["workflow_run_id"] = workflow_run_id
    built["created_at"] = datetime.now(UTC).isoformat()
    return built


def _build_public_message(stage: str, status: str, raw_message: str) -> str:
    if status == "running":
        return _build_running_message(stage, raw_message)
    if status == "success":
        return _build_success_message(stage, raw_message)
    if status == "failed":
        return _build_failed_message(stage, raw_message)

    stage_label = PUBLIC_STAGE_LABELS.get(stage, stage or "流程阶段")
    return f"{stage_label}状态已更新。"


def _build_running_message(stage: str, raw_message: str) -> str:
    lowered = raw_message.lower()
    if stage in {"lead.planning", "lead.research_development"} and ("revising" in lowered or "feedback" in lowered):
        return "正在根据质检意见修订策划方案与提示词。"
    if stage == "lead.production" and "reworking" in lowered:
        return "正在根据质检意见返工脚本与制作素材。"
    if stage == "lead.qa" and "reviewing the reworked" in lowered:
        return "正在复核返工后的生产结果。"
    return RUNNING_MESSAGES.get(stage, f"{PUBLIC_STAGE_LABELS.get(stage, stage or '流程阶段')}正在执行。")


def _build_success_message(stage: str, raw_message: str) -> str:
    lowered = raw_message.lower()
    if stage == "lead.qa" and "requested rework" in lowered:
        return "质量检查已完成，已提出返工建议。"
    return SUCCESS_MESSAGES.get(stage, f"{PUBLIC_STAGE_LABELS.get(stage, stage or '流程阶段')}已完成。")


def _build_failed_message(stage: str, raw_message: str) -> str:
    stage_label = PUBLIC_STAGE_LABELS.get(stage, stage or "流程阶段")
    prefix = f"{stage} failed:"
    if raw_message.lower().startswith(prefix.lower()):
        reason = raw_message[len(prefix):].strip()
    else:
        reason = raw_message.strip()

    if reason:
        return f"{stage_label}执行失败：{reason}"
    return f"{stage_label}执行失败。"


def _build_finance_artifact(*, stage: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    finance_check = payload.get("finance_check") if isinstance(payload.get("finance_check"), dict) else {}
    if not finance_check:
        return None
    details: list[str] = []
    if "passed" in finance_check:
        details.append(f"预算校验：{'通过' if finance_check.get('passed') else '未通过'}")
    if finance_check.get("message"):
        details.append(f"说明：{_normalize_text(finance_check.get('message'), 180)}")
    blocked_reasons = _normalize_list(finance_check.get("blocked_reasons"), limit=4, max_length=120)
    details.extend(f"限制：{item}" for item in blocked_reasons)
    return {
        "title": "预算校验结果已记录",
        "summary": details[0] if details else "财务闸门已完成记录。",
        "details": details,
        "message": "\n".join(details) if details else "财务闸门已完成记录。",
    }


def _build_research_artifact(*, stage: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    queries = _normalize_list(payload.get("expanded_queries"), limit=6, max_length=64)
    hotspots = payload.get("selected_hotspots") if isinstance(payload.get("selected_hotspots"), list) else []
    hotspot_pool = payload.get("hotspot_pool") if isinstance(payload.get("hotspot_pool"), list) else []
    details: list[str] = []
    if queries:
        details.append(f"搜索词：{' / '.join(queries)}")
    for index, item in enumerate(hotspot_pool[:8], start=1):
        details.append(
            f"候选{index}：{_hotspot_line(item, default_title='候选内容')}"
        )
    for item in hotspots[:6]:
        details.append(f"热点：{_hotspot_line(item, default_title='热点内容')}")
    if not details:
        return None
    summary = f"共整理 {len(hotspots)} 条入选热点，候选池 {len(hotspot_pool)} 条。"
    return {
        "title": "已找到热门视频",
        "summary": summary,
        "details": details,
        "message": "\n".join([summary, *details]),
    }


def _build_analysis_artifact(*, stage: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    reports = payload.get("analysis_reports") if isinstance(payload.get("analysis_reports"), list) else []
    details: list[str] = []
    for report in reports[:4]:
        report_data = _mapping(report)
        if not report_data:
            continue
        title = _normalize_text(report_data.get("report_title"), 80) or "爆款DNA报告"
        details.append(title)
        if report_data.get("framework_summary"):
            details.append(f"框架：{_normalize_text(report_data.get('framework_summary'), 200)}")
        if report_data.get("hook_design"):
            details.append(f"钩子：{_normalize_value(report_data.get('hook_design'), 120)}")
        if report_data.get("emotion_curve"):
            details.append(f"情绪：{_normalize_value(report_data.get('emotion_curve'), 120)}")
        reusable = _normalize_list(report_data.get("reusable_elements"), limit=6, max_length=48)
        if reusable:
            details.append(f"可复用：{' / '.join(reusable)}")
    if not details:
        return None
    summary = f"已输出 {len(reports)} 份爆款 DNA 摘要。"
    return {
        "title": "爆款基因分析完成",
        "summary": summary,
        "details": details,
        "message": "\n".join([summary, *details]),
    }


def _build_planning_artifact(*, stage: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    prompt_package = payload.get("prompt_package") if isinstance(payload.get("prompt_package"), dict) else payload
    details: list[str] = []
    for field, label, limit in (
        ("prompt_summary", "策略摘要", 180),
        ("script_topic", "脚本主题", 120),
        ("video_prompt", "主提示词", 240),
    ):
        value = _normalize_text(prompt_package.get(field), limit)
        if value:
            details.append(f"{label}：{value}")
    if isinstance(prompt_package.get("quality_score"), (int, float)):
        details.append(f"质量分：{round(float(prompt_package['quality_score']), 4)}")
    version_label = _normalize_text(prompt_package.get("version_label"), 64)
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
        values = _normalize_list(prompt_package.get(field), limit=6, max_length=120)
        if values:
            details.append(f"{label}：{' / '.join(values)}")
    if not details:
        return None
    summary = "技术策划已经完成提示词、标题与视觉指令整理。"
    return {
        "title": "新提示词已生成",
        "summary": summary,
        "details": details,
        "message": "\n".join([summary, *details]),
    }


def _build_production_artifact(*, stage: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    bundle = dict(payload)
    nested_bundle = bundle.get("bundle") if isinstance(bundle.get("bundle"), dict) else {}
    script = _mapping(nested_bundle.get("script")) or _mapping(bundle.get("script"))
    if not script:
        return None
    details: list[str] = []
    for field, label in (
        ("title", "标题"),
        ("topic", "主题"),
        ("hook", "开头"),
        ("cta", "结尾"),
    ):
        value = _normalize_text(script.get(field), 180)
        if value:
            details.append(f"{label}：{value}")
    tags = _normalize_list(script.get("tags"), limit=8, max_length=24)
    if tags:
        details.append(f"标签：{' / '.join(tags)}")
    scenes = script.get("scenes") if isinstance(script.get("scenes"), list) else []
    for index, scene in enumerate(scenes[:6], start=1):
        scene_data = _mapping(scene)
        if not scene_data:
            continue
        timing = _normalize_text(scene_data.get("timing") or scene_data.get("time"), 48) or "-"
        visuals = _normalize_text(scene_data.get("visuals") or scene_data.get("shot"), 140) or "-"
        text = _normalize_text(scene_data.get("text") or scene_data.get("caption"), 100) or "-"
        details.append(f"分镜{index}：{timing} | 画面：{visuals} | 字幕：{text}")
    if not details:
        return None
    summary = f"已生成 {len(scenes)} 个分镜片段。"
    return {
        "title": "脚本草案已生成",
        "summary": summary,
        "details": details,
        "message": "\n".join([summary, *details]),
    }


def _build_qa_artifact(*, stage: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    qa_report = payload.get("qa_report") if isinstance(payload.get("qa_report"), dict) else payload
    details: list[str] = []
    recommendation = _normalize_text(qa_report.get("recommendation"), 200)
    if recommendation:
        details.append(f"建议：{recommendation}")
    issues = _normalize_list(qa_report.get("issues"), limit=6, max_length=120)
    details.extend(f"检查项：{item}" for item in issues)
    checks = payload.get("checks") if isinstance(payload.get("checks"), list) else []
    for item in checks[:8]:
        normalized = _normalize_check(item)
        if normalized:
            details.append(normalized)
    summary_parts: list[str] = []
    if "pass" in qa_report:
        summary_parts.append("通过" if qa_report.get("pass") else "未通过")
    if qa_report.get("overall_score") is not None:
        summary_parts.append(f"评分 {qa_report.get('overall_score')}")
    summary = " / ".join(summary_parts) or "质检已完成。"
    if not details and not summary_parts:
        return None
    return {
        "title": "质检结果已归档",
        "summary": summary,
        "details": details,
        "message": "\n".join([summary, *details]) if details else summary,
    }


def _build_publish_artifact(*, stage: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    bundle = payload.get("bundle") if isinstance(payload.get("bundle"), dict) else payload
    publish_plan = bundle.get("publish_plan") if isinstance(bundle.get("publish_plan"), dict) else {}
    publish_result = bundle.get("publish_result") if isinstance(bundle.get("publish_result"), dict) else {}
    callback = bundle.get("callback") if isinstance(bundle.get("callback"), dict) else {}
    history = bundle.get("history") if isinstance(bundle.get("history"), dict) else {}
    details: list[str] = []
    for source_dict, fields in (
        (publish_plan, (("platform", "平台"), ("publish_goal", "发布目标"), ("audience", "受众"), ("video_url", "交付视频"))),
        (publish_result, (("publish_id", "发布单号"), ("status", "发布状态"))),
        (callback, (("callback_status", "回调状态"), ("callback_ref", "回调引用"))),
        (history, (("history_status", "历史归档"), ("history_ref", "历史引用"))),
    ):
        for field, label in fields:
            value = _normalize_text(source_dict.get(field), 240 if field == "video_url" else 120)
            if value:
                details.append(f"{label}：{value}")
    publish_steps = _normalize_list(publish_plan.get("publish_steps"), limit=8, max_length=48)
    if publish_steps:
        details.append(f"发布步骤：{' / '.join(publish_steps)}")
    if not details:
        return None
    summary = "发布执行结果、回调状态和归档信息已经记录。"
    return {
        "title": "对外交付结果已归档",
        "summary": summary,
        "details": details,
        "message": "\n".join([summary, *details]),
    }


def _hotspot_line(item: Any, *, default_title: str) -> str:
    item_data = _mapping(item)
    if not item_data:
        return default_title
    title = _normalize_text(item_data.get("title"), 80) or default_title
    author = _normalize_text(item_data.get("author"), 40) or "-"
    heat = _format_metric(item_data.get("heat_score"))
    views = _format_metric(item_data.get("view_count"))
    return f"{title} | 作者：{author} | 热度：{heat} | 播放：{views}"


def _mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if value is None:
        return None
    if hasattr(value, "__dict__"):
        return dict(vars(value))
    return None


def _normalize_text(value: Any, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return text[:limit]


def _normalize_list(value: Any, *, limit: int, max_length: int) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for entry in value:
        normalized = _normalize_value(entry, max_length)
        if normalized:
            items.append(normalized)
        if len(items) >= limit:
            break
    return items


def _normalize_value(value: Any, max_length: int) -> str | None:
    if isinstance(value, str):
        return _normalize_text(value, max_length)
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        parts = [item for item in (_normalize_value(item, max(16, max_length // 2)) for item in value[:4]) if item]
        return " / ".join(parts)[:max_length] if parts else None
    if isinstance(value, dict):
        parts = []
        for key, item in list(value.items())[:4]:
            normalized = _normalize_value(item, max(16, max_length // 3))
            if normalized:
                parts.append(f"{key}: {normalized}")
        return "；".join(parts)[:max_length] if parts else None
    return None


def _normalize_check(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    dimension = _normalize_text(value.get("dimension"), 48) or "未知维度"
    status = "通过" if value.get("pass") else "未通过"
    issues = _normalize_list(value.get("issues"), limit=2, max_length=72)
    if issues:
        return f"{dimension}：{status} | {'；'.join(issues)}"
    return f"{dimension}：{status}"


def _format_metric(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return "-"
