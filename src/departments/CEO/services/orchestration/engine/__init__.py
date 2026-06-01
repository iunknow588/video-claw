from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from departments.CEO.services.orchestration.pipeline import Pipeline, PipelineContext, PipelineResult
from departments.CIO.schemas.video import DomainWorkflowRequest

WorkflowEventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class WorkflowExecutionEngine:
    """Thin CEO orchestrator that coordinates departmental pipelines end to end."""

    def __init__(self, assembly: Any, recorder: Any):
        self.assembly = assembly
        self.recorder = recorder

    async def run_domain_workflow(
        self,
        request: DomainWorkflowRequest,
        *,
        event_callback: WorkflowEventCallback | None = None,
    ) -> dict[str, Any]:
        trace_id = uuid4().hex
        request_bundle = {**request.model_dump(), "trace_id": trace_id}
        run_record = None

        ceo_plan = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="ceo.workflow",
                skill=self.assembly.get_skill("ceo.workflow"),
                input_bundle=request_bundle,
                method_name="build_plan",
            )
        ).raw_output

        try:
            run_record = await self.assembly.workflow_run_service.create_run(
                trace_id=trace_id,
                workflow_type="domain_auto_run",
                domain=request.domain,
                platform=request.platform,
                audience=request.audience,
                publish_goal=request.publish_goal,
                content_type=request.content_type,
                style=request.style,
                video_style=request.video_style,
                duration=request.duration,
                expanded_queries=[],
            )
            context = PipelineContext(
                trace_id=trace_id,
                workflow_run_id=run_record.uuid,
                request=request,
            )
            await self.recorder.record_log(
                trace_id=trace_id,
                source="ceo.workflow",
                level="info",
                message="workflow accepted by CEO",
                workflow_run_id=run_record.uuid,
                context={"domain": request.domain, "platform": request.platform},
            )

            finance_result = await self._run_stage(
                stage="lead.cfo",
                message="CFO is validating the budget gate.",
                context=context,
                event_callback=event_callback,
                pipeline=self.assembly.finance_pipeline,
                input_bundle={},
            )
            finance_bundle = finance_result.bundle
            await self.recorder.record_artifact(
                trace_id=trace_id,
                source="lead.cfo",
                artifact_type="finance.bundle",
                payload=finance_bundle,
            )

            research_result = await self._run_stage(
                stage="lead.research",
                message="CSO is expanding queries and collecting hotspots.",
                context=context,
                event_callback=event_callback,
                pipeline=self.assembly.research_pipeline,
                input_bundle={},
            )
            if not research_result.bundle["selected_hotspots"]:
                raise ValueError("No hotspots available for the requested domain")
            await self.recorder.record_artifact(
                trace_id=trace_id,
                source="lead.research",
                artifact_type="research.bundle",
                payload=research_result.bundle["bundle"],
            )

            analysis_result = await self._run_stage(
                stage="lead.analysis",
                message="CCO is reverse engineering content structure and risks.",
                context=context,
                event_callback=event_callback,
                pipeline=self.assembly.analysis_pipeline,
                input_bundle={"hotspots": research_result.bundle["selected_hotspots"]},
            )
            await self.recorder.record_artifact(
                trace_id=trace_id,
                source="lead.analysis",
                artifact_type="analysis.bundle",
                payload=analysis_result.bundle["bundle"],
            )

            planning_result = await self._run_planning_stage(
                context=context,
                event_callback=event_callback,
                research_result=research_result,
                analysis_result=analysis_result,
                message="CTO is building the planning and prompt package.",
            )
            production_result = await self._run_production_stage(
                context=context,
                event_callback=event_callback,
                planning_result=planning_result,
                analysis_result=analysis_result,
                qa_feedback=None,
                message="COO is generating the script and production assets.",
            )
            qa_result = await self._run_qa_stage(
                context=context,
                event_callback=event_callback,
                planning_result=planning_result,
                analysis_result=analysis_result,
                production_result=production_result,
                message="CQO is running the quality gate.",
            )

            max_qa_rework_attempts = int(self.assembly.control_plane.get_qa_rework_policy().get("max_attempts", 1) or 0)
            qa_rework_attempts = 0
            while qa_result.status == "rework" and qa_rework_attempts < max_qa_rework_attempts:
                qa_rework_attempts += 1
                planning_result, production_result, qa_result = await self._run_qa_rework(
                    context=context,
                    event_callback=event_callback,
                    planning_result=planning_result,
                    analysis_result=analysis_result,
                    research_result=research_result,
                    qa_result=qa_result,
                    attempt=qa_rework_attempts,
                    max_attempts=max_qa_rework_attempts,
                )

            if qa_result.status == "rework":
                recommendation = qa_result.bundle["qa_report"]["recommendation"]
                await self.recorder.record_log(
                    trace_id=context.trace_id,
                    source="ceo.workflow",
                    level="error",
                    message="QA rework attempts exhausted",
                    workflow_run_id=context.workflow_run_id,
                    context={
                        "max_attempts": max_qa_rework_attempts,
                        "recommendation": recommendation,
                    },
                )
                raise ValueError(recommendation)

            publish_result = await self._run_stage(
                stage="lead.publish",
                message="CAO is preparing external delivery and publishing.",
                context=context,
                event_callback=event_callback,
                pipeline=self.assembly.publish_pipeline,
                input_bundle={
                    "production_bundle": production_result.bundle["bundle"],
                    "qa_bundle": qa_result.bundle,
                },
            )
            await self.recorder.record_artifact(
                trace_id=trace_id,
                source="lead.publish",
                artifact_type="publish.bundle",
                payload=publish_result.bundle["bundle"],
            )

            video_task = production_result.bundle.get("video_task")
            render_bundle = production_result.bundle["trace_bundle"]["render_bundle"]
            prompt_package_payload = {
                "selected_hotspot_ids": [item["uuid"] for item in research_result.bundle["selected_hotspots"]],
                **planning_result.bundle["prompt_package"],
            }
            video_url = (
                getattr(video_task, "video_url", None)
                if video_task is not None
                else render_bundle.get("delivery_asset_url")
            )
            result_payload = {
                "domain": request.domain,
                "platform": request.platform,
                "workflow_run_id": run_record.uuid,
                "trace_id": trace_id,
                "finance_bundle": finance_bundle,
                "expanded_queries": research_result.bundle["expanded_queries"],
                "selected_hotspots": research_result.bundle["selected_hotspots"],
                "prompt_package": prompt_package_payload,
                "analysis_ids": analysis_result.bundle["bundle"]["analysis_ids"],
                "script_id": production_result.bundle["script"].uuid,
                "script_status": production_result.bundle["script"].status,
                "qa_status": qa_result.bundle["qa_report"]["qa_status"],
                "video_task_id": getattr(video_task, "uuid", None),
                "video_status": getattr(video_task, "status", None) if video_task is not None else None,
                "video_url": video_url,
                "workflow_notes": [
                    *finance_result.notes,
                    *research_result.notes,
                    *analysis_result.notes,
                    *planning_result.notes,
                    *production_result.notes,
                    *qa_result.notes,
                    *publish_result.notes,
                ],
                "ceo_plan": ceo_plan.run_plan,
                "lead_route_list": ceo_plan.lead_route_list,
                "research_bundle": research_result.bundle["bundle"],
                "analysis_bundle": analysis_result.bundle["bundle"],
                "prompt_bundle": planning_result.bundle["prompt_bundle"],
                "production_bundle": production_result.bundle["trace_bundle"],
                "qa_bundle": qa_result.bundle["bundle"],
                "publish_bundle": publish_result.bundle["bundle"],
            }

            await self.assembly.workflow_run_service.mark_completed(
                run_record,
                expanded_queries=research_result.bundle["expanded_queries"],
                selected_hotspot_ids=[item["uuid"] for item in research_result.bundle["selected_hotspots"]],
                prompt_package=prompt_package_payload,
                analysis_ids=analysis_result.bundle["bundle"]["analysis_ids"],
                script_id=production_result.bundle["script"].uuid,
                video_task_id=getattr(video_task, "uuid", None),
                result_payload=result_payload,
            )
            await self.recorder.record_log(
                trace_id=trace_id,
                source="ceo.workflow",
                level="info",
                message="workflow completed",
                workflow_run_id=run_record.uuid,
                context={"qa_status": qa_result.bundle["qa_report"]["qa_status"]},
            )
            return result_payload
        except Exception as exc:
            if run_record is not None:
                await self.assembly.workflow_run_service.mark_failed(run_record, error_message=str(exc))
            await self.recorder.record_log(
                trace_id=trace_id,
                source="ceo.workflow",
                level="error",
                message="workflow failed",
                workflow_run_id=getattr(run_record, "uuid", None),
                context={"error": str(exc)},
            )
            raise

    async def _run_planning_stage(
        self,
        *,
        context: PipelineContext,
        event_callback: WorkflowEventCallback | None,
        research_result: PipelineResult,
        analysis_result: PipelineResult,
        message: str,
    ) -> PipelineResult:
        planning_result = await self._run_stage(
            stage="lead.research_development",
            message=message,
            context=context,
            event_callback=event_callback,
            pipeline=self.assembly.planning_pipeline,
            input_bundle={
                "hotspots": research_result.bundle["selected_hotspots"],
                "analyses": analysis_result.bundle["analysis_reports"],
            },
        )
        await self.recorder.record_artifact(
            trace_id=context.trace_id,
            source="lead.research_development",
            artifact_type="planning.bundle",
            payload=planning_result.bundle["prompt_bundle"],
        )
        return planning_result

    async def _run_production_stage(
        self,
        *,
        context: PipelineContext,
        event_callback: WorkflowEventCallback | None,
        planning_result: PipelineResult,
        analysis_result: PipelineResult,
        qa_feedback: str | None,
        message: str,
    ) -> PipelineResult:
        production_result = await self._run_stage(
            stage="lead.production",
            message=message,
            context=context,
            event_callback=event_callback,
            pipeline=self.assembly.production_pipeline,
            input_bundle={
                "planning_bundle": planning_result.bundle,
                "primary_analysis": analysis_result.bundle["analysis_reports"][0],
                "qa_feedback": qa_feedback,
            },
        )
        await self.recorder.record_artifact(
            trace_id=context.trace_id,
            source="lead.production",
            artifact_type="production.bundle",
            payload=production_result.bundle["trace_bundle"],
        )
        return production_result

    async def _run_qa_stage(
        self,
        *,
        context: PipelineContext,
        event_callback: WorkflowEventCallback | None,
        planning_result: PipelineResult,
        analysis_result: PipelineResult,
        production_result: PipelineResult,
        message: str,
    ) -> PipelineResult:
        qa_result = await self._run_stage(
            stage="lead.qa",
            message=message,
            context=context,
            event_callback=event_callback,
            pipeline=self.assembly.qa_pipeline,
            input_bundle={
                "prompt_bundle": planning_result.bundle["prompt_bundle"],
                "analysis_bundle": analysis_result.bundle["bundle"],
                "production_bundle": production_result.bundle["bundle"],
            },
        )
        await self.recorder.record_artifact(
            trace_id=context.trace_id,
            source="lead.qa",
            artifact_type="qa.bundle",
            payload=qa_result.bundle["bundle"],
        )
        return qa_result

    async def _run_qa_rework(
        self,
        *,
        context: PipelineContext,
        event_callback: WorkflowEventCallback | None,
        planning_result: PipelineResult,
        analysis_result: PipelineResult,
        research_result: PipelineResult,
        qa_result: PipelineResult,
        attempt: int,
        max_attempts: int,
    ) -> tuple[PipelineResult, PipelineResult, PipelineResult]:
        qa_report = qa_result.bundle["qa_report"]
        reroute = self.assembly.qa_reroute_service.determine_reroute(qa_report)
        await self.recorder.record_log(
            trace_id=context.trace_id,
            source="ceo.workflow",
            level="info",
            message="QA requested reroute",
            workflow_run_id=context.workflow_run_id,
            context={
                "attempt": attempt,
                "max_attempts": max_attempts,
                "strategy": reroute.strategy,
                "route_key": reroute.route_key,
                "target": reroute.target,
                "failed_dimensions": qa_report.get("failed_dimensions", []),
            },
        )

        qa_feedback = qa_report.get("recommendation")
        if reroute.target == "lead.research_development":
            planning_result = await self._run_planning_stage(
                context=context,
                event_callback=event_callback,
                research_result=research_result,
                analysis_result=analysis_result,
                message="CTO is revising the planning package based on CQO feedback.",
            )

        if reroute.target not in {"lead.production", "lead.research_development"}:
            raise ValueError(f"Unsupported QA reroute target: {reroute.target}")

        production_result = await self._run_production_stage(
            context=context,
            event_callback=event_callback,
            planning_result=planning_result,
            analysis_result=analysis_result,
            qa_feedback=qa_feedback,
            message="COO is reworking production based on CQO feedback.",
        )
        qa_result = await self._run_qa_stage(
            context=context,
            event_callback=event_callback,
            planning_result=planning_result,
            analysis_result=analysis_result,
            production_result=production_result,
            message="CQO is reviewing the reworked production output.",
        )
        return planning_result, production_result, qa_result

    async def _run_stage(
        self,
        *,
        stage: str,
        message: str,
        context: PipelineContext,
        event_callback: WorkflowEventCallback | None,
        pipeline: Pipeline,
        input_bundle: dict[str, Any],
    ) -> PipelineResult:
        await self.recorder.record_status(
            trace_id=context.trace_id,
            stage=stage,
            status="running",
            workflow_run_id=context.workflow_run_id,
            message=message,
            event_callback=event_callback,
        )
        try:
            result = await pipeline.run(context, input_bundle)
        except Exception as exc:
            await self.recorder.record_status(
                trace_id=context.trace_id,
                stage=stage,
                status="failed",
                workflow_run_id=context.workflow_run_id,
                message=f"{stage} failed: {exc}",
                event_callback=event_callback,
            )
            raise

        completion_message = f"{stage} completed"
        if result.status == "rework":
            completion_message = f"{stage} completed and requested rework"
        await self.recorder.record_status(
            trace_id=context.trace_id,
            stage=stage,
            status="success",
            workflow_run_id=context.workflow_run_id,
            message=completion_message,
            event_callback=event_callback,
        )
        return result
