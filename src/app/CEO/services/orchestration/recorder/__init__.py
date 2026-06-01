from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder

from app.CEO.skills.runtime import SkillInvocationResult
from app.CIO.services.event_bus import WorkflowEvent, WorkflowEventCallback


class WorkflowRecorder:
    """Thin orchestration recorder that delegates events to CIO event and observability services."""

    def __init__(self, assembly: Any):
        self.assembly = assembly
        self.assembly.recorder = self
        self.event_bus = assembly.event_bus
        self.trace_collector = assembly.trace_collector
        self.metrics_reporter = assembly.metrics_reporter

    async def record(
        self,
        event: WorkflowEvent,
        *,
        event_callback: WorkflowEventCallback | None = None,
    ) -> dict[str, Any]:
        persisted = await self.event_bus.publish(event, event_callback=event_callback)
        await self.trace_collector.append(event)
        await self.metrics_reporter.report(event)
        return persisted

    async def record_status(
        self,
        *,
        trace_id: str,
        stage: str,
        status: str,
        workflow_run_id: str,
        message: str,
        event_callback: WorkflowEventCallback | None = None,
    ) -> dict[str, Any]:
        event = WorkflowEvent(
            trace_id=trace_id,
            kind="status",
            source=stage,
            event_type="status",
            status=status,
            workflow_run_id=workflow_run_id,
            message=message,
            public_payload={
                "type": "status",
                "stage": stage,
                "status": status,
                "trace_id": trace_id,
                "workflow_run_id": workflow_run_id,
                "message": message,
            },
            metadata_json={"channel": "workflow_status"},
        )
        return await self.record(event, event_callback=event_callback)

    async def record_log(
        self,
        *,
        trace_id: str,
        source: str,
        level: str,
        message: str,
        workflow_run_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = WorkflowEvent(
            trace_id=trace_id,
            kind="log",
            source=source,
            event_type="log",
            workflow_run_id=workflow_run_id,
            level=level,
            message=message,
            metadata_json=dict(context or {}),
        )
        return await self.record(event)

    async def record_artifact(
        self,
        *,
        trace_id: str,
        source: str,
        artifact_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        event = WorkflowEvent(
            trace_id=trace_id,
            kind="artifact",
            source=source,
            event_type="artifact",
            status="stored",
            message=f"{artifact_type} stored",
            artifact_type=artifact_type,
            artifact_payload=dict(payload),
            metadata_json={"artifact_type": artifact_type},
        )
        return await self.record(event)

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
        await self.record(
            WorkflowEvent(
                trace_id=trace_id,
                kind="trace",
                source=skill_name,
                event_type="start",
                status="running",
                parent_id=parent_id,
                input_json=jsonable_encoder(input_bundle),
                metadata_json={"managed": True},
            )
        )
        try:
            invocation = await self.assembly.skill_runtime.invoke(
                skill,
                input_bundle,
                method_name=method_name,
            )
            await self.record(
                WorkflowEvent(
                    trace_id=trace_id,
                    kind="trace",
                    source=invocation.descriptor.name,
                    event_type="finish",
                    status="success",
                    parent_id=parent_id,
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
            )
            return invocation
        except Exception as exc:
            await self.record(
                WorkflowEvent(
                    trace_id=trace_id,
                    kind="trace",
                    source=skill_name,
                    event_type="fail",
                    status="failed",
                    parent_id=parent_id,
                    input_json=jsonable_encoder(input_bundle),
                    error_message=str(exc),
                    metadata_json={
                        "managed": True,
                        "tags": list(getattr(skill, "tags", []) or []),
                        "required_tokens": list(getattr(skill, "required_tokens", []) or []),
                    },
                )
            )
            raise
