"""
Workflow execution engine.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import traceback
import uuid

from departments.CEO.services.orchestration.pipeline import PipelineContext
from departments.CIO.schemas.video import DomainWorkflowRequest
from departments.CIO.services.event_bus import WorkflowEventCallback
from departments.CIO.services.workflow_runs import WorkflowRunService


class WorkflowExecutionEngine:
    """
    Orchestrates multi-stage workflow execution.

    Stages: CFO -> Research -> Analysis -> Planning -> Production -> QA -> Publish
    """

    def __init__(
        self,
        assembly,
        workflow_run_service: Optional[WorkflowRunService] = None,
        recorder=None,
    ):
        self.assembly = assembly
        self.workflow_run_service = (
            workflow_run_service
            or getattr(assembly, "workflow_run_service", None)
            or WorkflowRunService()
        )
        self.recorder = recorder or getattr(assembly, "recorder", None)
        self.control_plane = assembly.control_plane

    async def run_domain_workflow(
        self,
        request: DomainWorkflowRequest,
        *,
        trigger_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        event_callback: WorkflowEventCallback | None = None,
    ) -> Dict[str, Any]:
        """Execute complete domain workflow."""
        trace_id = trace_id or str(uuid.uuid4())

        run = await self.workflow_run_service.create_run(
            trace_id=trace_id,
            workflow_type="domain_auto_run",
            domain=request.domain,
            platform=request.platform,
            input_params=request.model_dump(),
            trigger_id=trigger_id,
        )

        workflow_run_id = run.uuid
        context = PipelineContext(trace_id=trace_id, workflow_run_id=workflow_run_id, request=request)

        try:
            failed_stage = "CFO"
            cfo_result = await self._run_stage(
                "lead.cfo",
                context=context,
                input_bundle={},
                event_callback=event_callback,
            )
            await self._record_artifact(trace_id, "lead.cfo", "finance_bundle", cfo_result)

            failed_stage = "Research"
            research_result = await self._run_stage(
                "lead.research",
                context=context,
                input_bundle={},
                event_callback=event_callback,
            )
            await self._record_artifact(trace_id, "lead.research", "research_bundle", research_result)

            failed_stage = "Analysis"
            analysis_result = await self._run_stage(
                "lead.analysis",
                context=context,
                input_bundle={"hotspots": research_result.get("selected_hotspots", [])},
                event_callback=event_callback,
            )
            await self._record_artifact(trace_id, "lead.analysis", "analysis_bundle", analysis_result)

            failed_stage = "Planning"
            planning_result = await self._run_stage(
                "lead.planning",
                context=context,
                input_bundle={
                    "hotspots": research_result.get("selected_hotspots", []),
                    "analyses": analysis_result.get("analysis_reports", []),
                },
                event_callback=event_callback,
            )
            await self._record_artifact(trace_id, "lead.research_development", "planning_bundle", planning_result)

            failed_stage = "Production"
            production_result = await self._run_stage(
                "lead.production",
                context=context,
                input_bundle={
                    "planning_bundle": planning_result,
                    "primary_analysis": self._extract_primary_analysis(analysis_result),
                    "qa_feedback": None,
                },
                event_callback=event_callback,
            )
            await self._record_artifact(trace_id, "lead.production", "production_bundle", production_result)

            failed_stage = "QA"
            planning_result, production_result, qa_result = await self._run_qa_stage(
                context=context,
                research_result=research_result,
                analysis_result=analysis_result,
                planning_result=planning_result,
                production_result=production_result,
                trace_id=trace_id,
                event_callback=event_callback,
            )

            failed_stage = "Publish"
            publish_result = await self._run_stage(
                "lead.publish",
                context=context,
                input_bundle={
                    "production_bundle": self._resolve_stage_bundle(production_result),
                    "qa_bundle": qa_result,
                },
                event_callback=event_callback,
            )
            await self._record_artifact(trace_id, "lead.publish", "publish_bundle", publish_result)

            result_payload = self._build_result_payload(
                workflow_run_id=workflow_run_id,
                trace_id=trace_id,
                trigger_id=trigger_id,
                domain=request.domain,
                platform=request.platform,
                input_params=request.model_dump(),
                cfo_result=cfo_result,
                research_result=research_result,
                analysis_result=analysis_result,
                planning_result=planning_result,
                production_result=production_result,
                qa_result=qa_result,
                publish_result=publish_result,
            )

            await self._mark_run_completed(run, result_payload)
            return result_payload

        except Exception as exc:
            failure_context = await self._build_failure_context(
                workflow_run_id=workflow_run_id,
                trace_id=trace_id,
                trigger_id=trigger_id,
                domain=request.domain,
                platform=request.platform,
                input_params=request.model_dump(),
                failed_stage=failed_stage,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            await self._mark_run_failed(run, failure_context, str(exc))
            raise

    async def _run_stage(
        self,
        lead_role: str,
        *,
        context: PipelineContext,
        input_bundle: Dict[str, Any],
        event_callback: WorkflowEventCallback | None = None,
    ) -> Dict[str, Any]:
        """Execute a single workflow stage against the pipeline contract."""
        pipeline_map = {
            "lead.cfo": self.assembly.finance_pipeline,
            "lead.research": self.assembly.research_pipeline,
            "lead.analysis": self.assembly.analysis_pipeline,
            "lead.planning": self.assembly.planning_pipeline,
            "lead.production": self.assembly.production_pipeline,
            "lead.qa": self.assembly.qa_pipeline,
            "lead.publish": self.assembly.publish_pipeline,
        }

        pipeline = pipeline_map.get(lead_role)
        if not pipeline:
            raise ValueError(f"Unknown lead_role: {lead_role}")

        await self._record_stage_status(
            trace_id=context.trace_id,
            workflow_run_id=context.workflow_run_id,
            stage=lead_role,
            status="running",
            message=self._build_stage_status_message(lead_role, "running"),
            event_callback=event_callback,
        )

        try:
            if hasattr(pipeline, "run"):
                result = await pipeline.run(context, input_bundle)
                normalized = self._normalize_stage_result(result)
            elif hasattr(pipeline, "execute"):
                result = await pipeline.execute(**input_bundle)
                normalized = self._normalize_stage_result(result)
            else:
                raise TypeError(f"Pipeline for {lead_role} does not expose run() or execute()")
        except Exception as exc:
            await self._record_stage_status(
                trace_id=context.trace_id,
                workflow_run_id=context.workflow_run_id,
                stage=lead_role,
                status="failed",
                message=self._build_stage_status_message(lead_role, "failed", detail=str(exc)),
                event_callback=event_callback,
            )
            raise

        normalized_status = "success"
        normalized_message = self._build_stage_status_message(lead_role, "success")
        if lead_role == "lead.qa" and normalized.get("status") == "rework":
            normalized_message = self._build_stage_status_message(lead_role, "success", detail="requested rework")

        await self._record_stage_status(
            trace_id=context.trace_id,
            workflow_run_id=context.workflow_run_id,
            stage=lead_role,
            status=normalized_status,
            message=normalized_message,
            event_callback=event_callback,
        )
        return normalized

    async def _run_qa_stage(
        self,
        *,
        context: PipelineContext,
        research_result: Dict[str, Any],
        analysis_result: Dict[str, Any],
        planning_result: Dict[str, Any],
        production_result: Dict[str, Any],
        trace_id: str,
        event_callback: WorkflowEventCallback | None = None,
    ) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """
        Run QA stage with rework loop.

        Supports configurable max rework attempts from control plane.
        """
        qa_policy = self.control_plane.get_qa_rework_policy()
        max_reworks = max(
            int(
                qa_policy.get(
                    "max_rework_attempts",
                    qa_policy.get("max_attempts", 1),
                )
                or 0
            ),
            0,
        )
        total_attempts = max_reworks + 1

        attempt = 0
        qa_result: Dict[str, Any] | None = None

        while attempt < total_attempts:
            attempt += 1
            qa_result = await self._run_stage(
                "lead.qa",
                context=context,
                input_bundle={
                    "prompt_bundle": planning_result.get("prompt_bundle", {}),
                    "analysis_bundle": analysis_result.get("bundle", {}),
                    "production_bundle": self._resolve_stage_bundle(production_result),
                },
                event_callback=event_callback,
            )

            await self._record_artifact(trace_id, "lead.qa", "qa_bundle", qa_result)

            if qa_result.get("status") != "rework":
                break

            if attempt >= total_attempts:
                break

            qa_report = qa_result.get("qa_report", qa_result)
            reroute = self.assembly.qa_reroute_service.determine_reroute(qa_report)
            qa_feedback = qa_report.get("recommendation")

            await self._record_log(
                trace_id=trace_id,
                source="lead.qa",
                workflow_run_id=context.workflow_run_id,
                level="warning",
                message="QA requested reroute",
                context={
                    "target": reroute.target,
                    "route_key": reroute.route_key,
                    "strategy": reroute.strategy,
                    "attempt": attempt,
                },
            )

            if reroute.target == "lead.research_development":
                planning_result = await self._run_stage(
                    "lead.planning",
                    context=context,
                    input_bundle={
                        "hotspots": research_result.get("selected_hotspots", []),
                        "analyses": analysis_result.get("analysis_reports", []),
                    },
                    event_callback=event_callback,
                )
                await self._record_artifact(
                    trace_id,
                    "lead.research_development",
                    "planning_bundle",
                    planning_result,
                )

            production_result = await self._run_stage(
                "lead.production",
                context=context,
                input_bundle={
                    "planning_bundle": planning_result,
                    "primary_analysis": self._extract_primary_analysis(analysis_result),
                    "qa_feedback": qa_feedback,
                },
                event_callback=event_callback,
            )
            await self._record_artifact(
                trace_id,
                "lead.production",
                "production_bundle",
                production_result,
            )

        if qa_result is None:
            raise ValueError("QA stage produced no result")

        if qa_result.get("status") == "rework":
            recommendation = qa_result.get("qa_report", {}).get("recommendation") or qa_result.get(
                "recommendation", "Manual review required"
            )
            raise ValueError(f"QA failed after {total_attempts} attempts: {recommendation}")

        return planning_result, production_result, qa_result

    def _build_result_payload(self, **kwargs) -> Dict[str, Any]:
        """Build success result payload."""
        research_result = kwargs.get("research_result", {}) or {}
        analysis_result = kwargs.get("analysis_result", {}) or {}
        planning_result = kwargs.get("planning_result", {}) or {}
        production_result = kwargs.get("production_result", {}) or {}
        qa_result = kwargs.get("qa_result", {}) or {}
        publish_result = kwargs.get("publish_result", {}) or {}

        production_bundle = self._resolve_stage_bundle(production_result)
        script = production_bundle.get("script")
        video_task = production_bundle.get("video_task")
        render_bundle = production_bundle.get("render_bundle", {}) or {}
        publish_bundle = publish_result.get("bundle", {}) or {}
        qa_report = qa_result.get("qa_report", {}) or {}

        video_url = (
            getattr(video_task, "video_url", None)
            or render_bundle.get("delivery_asset_url")
        )

        return {
            "workflow_run_id": kwargs.get("workflow_run_id"),
            "trace_id": kwargs.get("trace_id"),
            "trigger_id": kwargs.get("trigger_id"),
            "domain": kwargs.get("domain"),
            "platform": kwargs.get("platform"),
            "input_params": {
                "domain": kwargs.get("domain"),
                "platform": kwargs.get("platform"),
                **(kwargs.get("input_params") or {}),
            },
            "status": "completed",
            "finance_bundle": kwargs.get("cfo_result"),
            "expanded_queries": research_result.get("expanded_queries", []),
            "selected_hotspots": research_result.get("selected_hotspots", []),
            "prompt_package": {
                "selected_hotspot_ids": [
                    item.get("uuid")
                    for item in research_result.get("selected_hotspots", [])
                    if isinstance(item, dict) and item.get("uuid")
                ],
                **(planning_result.get("prompt_package", {}) or {}),
            },
            "analysis_ids": analysis_result.get("bundle", {}).get("analysis_ids", []),
            "script_id": getattr(script, "uuid", None) or production_result.get("script_id"),
            "script_status": getattr(script, "status", None) or production_result.get("script_status"),
            "qa_status": qa_report.get("qa_status") or qa_result.get("status"),
            "video_task_id": getattr(video_task, "uuid", None) or production_result.get("video_task_id"),
            "video_status": getattr(video_task, "status", None) or production_result.get("video_status"),
            "video_url": video_url,
            "publish_status": publish_bundle.get("publish_result", {}).get("status"),
            "workflow_notes": self._aggregate_notes(kwargs),
            "research_bundle": research_result.get("bundle"),
            "analysis_bundle": analysis_result.get("bundle"),
            "prompt_bundle": planning_result.get("prompt_bundle"),
            "production_bundle": self._serialize_production_bundle(production_result),
            "qa_bundle": self._serialize_qa_bundle(qa_result),
            "publish_bundle": publish_bundle,
        }

    async def _build_failure_context(self, **kwargs) -> Dict[str, Any]:
        """Build failure context with all available artifacts."""
        return {
            "workflow_run_id": kwargs.get("workflow_run_id"),
            "trace_id": kwargs.get("trace_id"),
            "trigger_id": kwargs.get("trigger_id"),
            "domain": kwargs.get("domain"),
            "platform": kwargs.get("platform"),
            "input_params": {
                "domain": kwargs.get("domain"),
                "platform": kwargs.get("platform"),
                **(kwargs.get("input_params") or {}),
            },
            "status": "failed",
            "failed_stage": kwargs.get("failed_stage"),
            "error": kwargs.get("error"),
            "traceback": kwargs.get("traceback"),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _aggregate_notes(self, kwargs: Dict[str, Any]) -> List[str]:
        """Aggregate notes from all stages."""
        notes: List[str] = []
        for key in [
            "cfo_result",
            "research_result",
            "analysis_result",
            "planning_result",
            "production_result",
            "qa_result",
            "publish_result",
        ]:
            result = kwargs.get(key, {}) or {}
            if result and "notes" in result:
                notes.extend(result["notes"])
        return notes

    def _normalize_stage_result(self, result: Any) -> Dict[str, Any]:
        if hasattr(result, "bundle") and hasattr(result, "status") and hasattr(result, "notes"):
            payload = dict(result.bundle or {})
            payload["status"] = result.status
            payload["notes"] = list(result.notes or [])
            return payload
        if isinstance(result, dict):
            return dict(result)
        raise TypeError(f"Unsupported stage result type: {type(result)!r}")

    def _extract_primary_analysis(self, analysis_result: Dict[str, Any]) -> Any:
        analyses = analysis_result.get("analysis_reports") or []
        return analyses[0] if analyses else None

    def _resolve_stage_bundle(self, stage_result: Dict[str, Any]) -> Dict[str, Any]:
        bundle = dict(stage_result or {})
        nested_bundle = bundle.pop("bundle", None)
        trace_bundle = bundle.pop("trace_bundle", None)
        resolved: Dict[str, Any] = {}
        if isinstance(nested_bundle, dict):
            resolved.update(nested_bundle)
        if isinstance(trace_bundle, dict):
            resolved = {**trace_bundle, **resolved}
        resolved = {**resolved, **bundle}
        return resolved

    def _serialize_production_bundle(self, production_result: Dict[str, Any]) -> Dict[str, Any]:
        production_bundle = self._resolve_stage_bundle(production_result)
        script = production_bundle.get("script")
        video_task = production_bundle.get("video_task")
        return {
            **production_bundle,
            "script": self._serialize_script(script),
            "video_task": self._serialize_video_task(video_task),
        }

    def _serialize_qa_bundle(self, qa_result: Dict[str, Any]) -> Dict[str, Any]:
        qa_bundle = dict(qa_result.get("bundle", {}) or {})
        qa_bundle.setdefault("qa_report", qa_result.get("qa_report"))
        checks = qa_bundle.get("checks") if isinstance(qa_bundle.get("checks"), list) else []
        qa_bundle["failed_dimensions"] = [
            check for check in checks
            if isinstance(check, dict) and check.get("applicable") and not check.get("pass")
        ]
        qa_bundle["total_checks"] = len(checks)
        qa_bundle["applicable_checks"] = sum(
            1 for check in checks
            if isinstance(check, dict) and check.get("applicable")
        )
        qa_bundle["passed_checks"] = sum(
            1 for check in checks
            if isinstance(check, dict) and check.get("applicable") and check.get("pass")
        )
        return qa_bundle

    async def _record_artifact(
        self,
        trace_id: str,
        source: str,
        artifact_type: str,
        payload: Dict[str, Any],
    ) -> None:
        if not self.recorder or not hasattr(self.recorder, "record_artifact"):
            return
        await self.recorder.record_artifact(
            trace_id=trace_id,
            source=source,
            artifact_type=artifact_type,
            payload=payload,
        )

    async def _record_log(
        self,
        *,
        trace_id: str,
        source: str,
        workflow_run_id: str,
        level: str,
        message: str,
        context: Dict[str, Any],
    ) -> None:
        if not self.recorder or not hasattr(self.recorder, "record_log"):
            return
        await self.recorder.record_log(
            trace_id=trace_id,
            source=source,
            workflow_run_id=workflow_run_id,
            level=level,
            message=message,
            context=context,
        )

    async def _record_stage_status(
        self,
        *,
        trace_id: str,
        workflow_run_id: str,
        stage: str,
        status: str,
        message: str,
        event_callback: WorkflowEventCallback | None,
    ) -> None:
        if not self.recorder or not hasattr(self.recorder, "record_status"):
            return
        await self.recorder.record_status(
            trace_id=trace_id,
            stage=stage,
            status=status,
            workflow_run_id=workflow_run_id,
            message=message,
            event_callback=event_callback,
        )

    def _build_stage_status_message(self, stage: str, status: str, detail: str | None = None) -> str:
        if status == "running":
            return f"{stage} started"
        if status == "failed":
            return f"{stage} failed: {detail or 'unknown error'}"
        if detail:
            return f"{stage} completed: {detail}"
        return f"{stage} completed"

    async def _mark_run_completed(self, run: Any, result_payload: Dict[str, Any]) -> None:
        await self.workflow_run_service.update_run_status(
            run_id=run.id,
            status="completed",
            result_payload=result_payload,
        )

    async def _mark_run_failed(self, run: Any, failure_context: Dict[str, Any], error_message: str) -> None:
        await self.workflow_run_service.update_run_status(
            run_id=run.id,
            status="failed",
            result_payload=failure_context,
        )

    def _serialize_script(self, script: Any) -> Any:
        if script is None:
            return None
        serializer = getattr(self.assembly, "serialize_script", None)
        if callable(serializer):
            return serializer(script)
        if hasattr(script, "__dict__"):
            return dict(vars(script))
        return script

    def _serialize_video_task(self, video_task: Any) -> Any:
        if video_task is None:
            return None
        serializer = getattr(self.assembly, "serialize_video_task", None)
        if callable(serializer):
            return serializer(video_task)
        if hasattr(video_task, "__dict__"):
            return dict(vars(video_task))
        return video_task
