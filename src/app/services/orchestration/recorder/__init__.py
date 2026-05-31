from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi.encoders import jsonable_encoder

from app.skills.catalog import SKILL_METADATA_OVERRIDES
from app.skills.runtime import SkillInvocationResult

WorkflowEventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class WorkflowExecutionRecorder:
    """Owns managed skill invocation, event emission, and CIO bundle persistence."""

    def __init__(self, assembly: Any):
        self.assembly = assembly

    async def record_stage(
        self,
        *,
        trace_id: str,
        skill_name: str,
        event_type: str,
        status: str,
        parent_id: str | None = None,
        input_json: dict[str, Any] | None = None,
        output_json: dict[str, Any] | None = None,
        error_message: str | None = None,
        cost: int = 0,
        metadata_json: dict[str, Any] | None = None,
    ) -> Any:
        return await self.assembly.workflow_step_service.record_step(
            trace_id=trace_id,
            skill_name=skill_name,
            event_type=event_type,
            status=status,
            parent_id=parent_id,
            input_json=input_json,
            output_json=output_json,
            error_message=error_message,
            cost=cost,
            metadata_json=metadata_json,
        )

    async def emit_event(
        self,
        event_callback: WorkflowEventCallback | None,
        event: dict[str, Any],
    ) -> None:
        if not event_callback:
            return
        maybe_awaitable = event_callback(event)
        if inspect.isawaitable(maybe_awaitable):
            await maybe_awaitable

    async def store_cio_bundle(
        self,
        *,
        trace_id: str,
        artifact_type: str,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        return (
            await self.call_skill(
                trace_id=trace_id,
                parent_id="lead.cio",
                skill=self.assembly.cio_store_skill,
                input_bundle={
                    "trace_id": trace_id,
                    "artifact_type": artifact_type,
                    "payload": payload,
                    "source": source,
                },
            )
        ).output_json["artifact"]

    async def call_skill(
        self,
        *,
        trace_id: str,
        parent_id: str,
        skill: Any,
        input_bundle: dict[str, Any],
        method_name: str | None = None,
    ) -> SkillInvocationResult:
        skill_name = getattr(skill, "skill_name", None) or getattr(skill, "name", None) or skill.__class__.__name__
        overrides = SKILL_METADATA_OVERRIDES.get(skill_name, {})
        await self.record_stage(
            trace_id=trace_id,
            parent_id=parent_id,
            skill_name=skill_name,
            event_type="start",
            status="running",
            input_json=jsonable_encoder(input_bundle),
            metadata_json={"managed": True},
        )
        try:
            invocation = await self.assembly.skill_runtime.invoke(
                skill,
                input_bundle,
                descriptor_overrides=overrides,
                method_name=method_name,
            )
            await self.record_stage(
                trace_id=trace_id,
                parent_id=parent_id,
                skill_name=invocation.descriptor.name,
                event_type="finish",
                status="success",
                input_json=jsonable_encoder(input_bundle),
                output_json=jsonable_encoder(invocation.output_json),
                metadata_json={
                    "managed": True,
                    "tags": invocation.descriptor.tags,
                    "dependencies": invocation.descriptor.dependencies,
                    "required_tokens": invocation.descriptor.required_tokens,
                    "retry_policy": invocation.descriptor.retry_policy,
                    "retry_count": invocation.retry_count,
                    "duration_ms": invocation.duration_ms,
                    "token_usage": invocation.token_usage.to_dict(),
                },
            )
            return invocation
        except Exception as exc:
            await self.record_stage(
                trace_id=trace_id,
                parent_id=parent_id,
                skill_name=skill_name,
                event_type="fail",
                status="failed",
                input_json=jsonable_encoder(input_bundle),
                error_message=str(exc),
                metadata_json={
                    "managed": True,
                    "tags": overrides.get("tags", []),
                    "required_tokens": overrides.get("required_tokens", []),
                },
            )
            raise
