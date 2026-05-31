from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class SkillStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


@dataclass(slots=True)
class SkillEnvelope:
    trace_id: str
    parent_id: str | None
    skill_name: str
    status: SkillStatus = SkillStatus.PENDING
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    cost: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class SkillResult:
    envelope: SkillEnvelope
    summary: str = ""


@dataclass(slots=True)
class CEOPlanBundle:
    trace_id: str
    run_plan: dict[str, Any]
    lead_route_list: list[str]
    dependency_order: list[str]
    policy: dict[str, Any]


@dataclass(slots=True)
class LogBundle:
    trace_id: str
    event_id: str
    ack: bool
    log_ref: str


@dataclass(slots=True)
class ResearchBundle:
    trace_id: str
    expanded_queries: list[str]
    hotspot_pool: list[dict[str, Any]]
    selected_hotspots: list[dict[str, Any]]
    snapshot: dict[str, Any]


@dataclass(slots=True)
class AnalysisBundle:
    trace_id: str
    analysis_reports: list[dict[str, Any]]
    analysis_ids: list[str]


@dataclass(slots=True)
class PromptBundle:
    trace_id: str
    prompt_package: dict[str, Any]
    title_candidates: list[str]
    validation: dict[str, Any]
    version: int


@dataclass(slots=True)
class ProductionBundle:
    trace_id: str
    script: dict[str, Any] | None
    video_task: dict[str, Any] | None
    script_bundle: dict[str, Any]
    notes: list[str]


@dataclass(slots=True)
class PublishBundle:
    trace_id: str
    publish_plan: dict[str, Any]
    platform_payload: dict[str, Any]
    publish_result: dict[str, Any]
    callback: dict[str, Any]
    history: dict[str, Any]
    retry: dict[str, Any]
