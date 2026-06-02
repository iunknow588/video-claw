from __future__ import annotations

from typing import Any


PUBLIC_STAGE_LABELS = {
    "lead.cfo": "财务闸门",
    "lead.research": "热点调研",
    "lead.analysis": "内容分析",
    "lead.research_development": "技术策划",
    "lead.production": "生产执行",
    "lead.qa": "质量检查",
    "lead.publish": "对外交付",
}

STAGE_IDENTITY_KEYS = {
    "lead.cfo": "cfo",
    "lead.research": "cso",
    "lead.analysis": "cco",
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
    "lead.research_development": "正在整理策划方案与提示词。",
    "lead.production": "正在生成脚本与制作素材。",
    "lead.qa": "正在进行质量检查。",
    "lead.publish": "正在整理交付结果并准备对外回传。",
}

SUCCESS_MESSAGES = {
    "lead.cfo": "预算校验已通过，流程继续推进。",
    "lead.research": "热点检索已完成，已整理候选内容。",
    "lead.analysis": "爆款基因分析已完成。",
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
    if stage == "lead.research_development" and ("revising" in lowered or "feedback" in lowered):
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
        reason = raw_message[len(prefix) :].strip()
    else:
        reason = raw_message.strip()

    if reason:
        return f"{stage_label}执行失败：{reason}"
    return f"{stage_label}执行失败。"
