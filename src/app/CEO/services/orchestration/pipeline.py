from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from app.CIO.schemas.video import DomainWorkflowRequest

PipelineStatus = Literal["success", "failed", "rework"]


@dataclass(slots=True)
class PipelineContext:
    trace_id: str
    workflow_run_id: str
    request: DomainWorkflowRequest


@dataclass(slots=True)
class PipelineResult:
    status: PipelineStatus
    bundle: dict[str, Any]
    notes: list[str]

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        status: PipelineStatus = "success",
    ) -> PipelineResult:
        bundle = dict(payload)
        notes = list(bundle.pop("notes", []))
        return cls(status=status, bundle=bundle, notes=notes)


class Pipeline(Protocol):
    async def run(self, context: PipelineContext, input_bundle: dict[str, Any]) -> PipelineResult:
        ...
