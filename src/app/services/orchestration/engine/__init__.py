from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi.encoders import jsonable_encoder

from app.models.analysis import AnalysisReport
from app.schemas.video import DomainWorkflowRequest, HotspotFetchRequest


class WorkflowExecutionEngine:
    """Executes the production workflow using assembled skills and recording hooks."""

    def __init__(self, assembly: Any, recorder: Any):
        self.assembly = assembly
        self.recorder = recorder

    async def run_domain_workflow(
        self,
        request: DomainWorkflowRequest,
        *,
        event_callback: Any | None = None,
    ) -> dict[str, Any]:
        trace_id = uuid4().hex
        request_bundle = request.model_dump()
        request_bundle["trace_id"] = trace_id

        ceo_plan = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="ceo.workflow",
                skill=self.assembly.ceo_skill,
                input_bundle=request_bundle,
                method_name="build_plan",
            )
        ).raw_output
        await self.recorder.record_stage(
            trace_id=trace_id,
            skill_name=self.assembly.ceo_skill.skill_name,
            event_type="start",
            status="running",
            input_json=request_bundle,
            output_json=ceo_plan.run_plan,
            metadata_json={"lead_route_list": ceo_plan.lead_route_list},
        )

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
        await self.recorder.emit_event(
            event_callback,
            {
                "type": "status",
                "stage": "ceo.workflow",
                "status": "running",
                "trace_id": trace_id,
                "workflow_run_id": run_record.uuid,
                "message": f"任务已接收，CEO 正在为“{request.domain}”规划执行路径。",
            },
        )

        try:
            start_event = (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="ceo.workflow",
                    skill=self.assembly.log_skill,
                    input_bundle={
                        "trace_id": trace_id,
                        "skill_name": self.assembly.ceo_skill.skill_name,
                        "event_type": "start",
                        "status": "running",
                        "input": request_bundle,
                        "output": ceo_plan.run_plan,
                        "cost": 0.0,
                    },
                    method_name="record",
                )
            ).raw_output
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.cio",
                skill=self.assembly.cio_log_skill,
                input_bundle={
                    "trace_id": trace_id,
                    "level": "info",
                    "message": "workflow accepted by CEO",
                    "context": {
                        "workflow_run_id": run_record.uuid,
                        "domain": request.domain,
                        "platform": request.platform,
                    },
                },
            )

            finance_input = {
                "domain": request.domain,
                "platform": request.platform,
                "duration": request.duration,
                "hotspot_count": request.hotspot_count,
                "top_n": request.top_n,
                "auto_generate_video": request.auto_generate_video,
            }
            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name="lead.cfo",
                event_type="start",
                status="running",
                input_json=finance_input,
            )
            await self.recorder.emit_event(
                event_callback,
                {
                    "type": "status",
                    "stage": "lead.cfo",
                    "status": "running",
                    "trace_id": trace_id,
                    "workflow_run_id": run_record.uuid,
                    "message": "CFO 正在预估本次任务花费并验证预算与模型配额。",
                },
            )
            try:
                finance_bundle = await self._run_finance_gate(
                    trace_id=trace_id,
                    workflow_run_id=run_record.uuid,
                    request=request,
                )
            except Exception as exc:
                await self.recorder.record_stage(
                    trace_id=trace_id,
                    skill_name="lead.cfo",
                    event_type="finish",
                    status="failed",
                    input_json=finance_input,
                    error_message=str(exc),
                )
                await self.recorder.emit_event(
                    event_callback,
                    {
                        "type": "status",
                        "stage": "lead.cfo",
                        "status": "failed",
                        "trace_id": trace_id,
                        "workflow_run_id": run_record.uuid,
                        "message": f"CFO 未放行，任务已被财务闸门拦截：{exc}",
                    },
                )
                raise
            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name="lead.cfo",
                event_type="finish",
                status="success",
                input_json=finance_input,
                output_json=finance_bundle,
            )
            await self.recorder.store_cio_bundle(
                trace_id=trace_id,
                artifact_type="finance.bundle",
                payload=finance_bundle,
                source="lead.cfo",
            )
            await self.recorder.emit_event(
                event_callback,
                {
                    "type": "status",
                    "stage": "lead.cfo",
                    "status": "success",
                    "trace_id": trace_id,
                    "workflow_run_id": run_record.uuid,
                    "message": (
                        f"CFO 已放行，预估 {finance_bundle['finance_estimate']['estimated_tokens']} tokens，"
                        f"预留 {finance_bundle['receipt']['amount']:.4f} USD。"
                    ),
                },
            )

            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name="lead.research",
                event_type="start",
                status="running",
                input_json={"domain": request.domain, "platform": request.platform},
            )
            await self.recorder.emit_event(
                event_callback,
                {
                    "type": "status",
                    "stage": "lead.research",
                    "status": "running",
                    "trace_id": trace_id,
                    "workflow_run_id": run_record.uuid,
                    "message": "调研组开始采集热点并做去重排序。",
                },
            )
            expanded_queries = (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.research",
                    skill=self.assembly.domain_query_skill,
                    input_bundle={
                        "domain": request.domain,
                        "audience": request.audience,
                        "publish_goal": request.publish_goal,
                        "trace_id": trace_id,
                    },
                )
            ).output_json["expanded_queries"]
            research_bundle = await self._run_research(
                trace_id=trace_id,
                request=request,
                expanded_queries=expanded_queries,
            )
            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name="lead.research",
                event_type="finish",
                status="success",
                input_json={"expanded_queries": expanded_queries},
                output_json=research_bundle["bundle"],
            )
            await self.recorder.store_cio_bundle(
                trace_id=trace_id,
                artifact_type="research.bundle",
                payload=research_bundle["bundle"],
                source="lead.research",
            )
            await self.recorder.emit_event(
                event_callback,
                {
                    "type": "status",
                    "stage": "lead.research",
                    "status": "success",
                    "trace_id": trace_id,
                    "workflow_run_id": run_record.uuid,
                    "message": f"调研完成，已选出 {len(research_bundle['selected_hotspots'])} 个候选热点。",
                },
            )
            selected_hotspots = research_bundle["selected_hotspots"]
            if not selected_hotspots:
                raise ValueError("No hotspots available for the requested domain")

            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name="lead.analysis",
                event_type="start",
                status="running",
                input_json={"hotspots": selected_hotspots},
            )
            await self.recorder.emit_event(
                event_callback,
                {
                    "type": "status",
                    "stage": "lead.analysis",
                    "status": "running",
                    "trace_id": trace_id,
                    "workflow_run_id": run_record.uuid,
                    "message": "分析组正在拆解爆款结构、钩子和风险点。",
                },
            )
            analysis_bundle = await self._run_analysis(trace_id=trace_id, hotspots=selected_hotspots)
            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name="lead.analysis",
                event_type="finish",
                status="success",
                input_json={"hotspots": selected_hotspots},
                output_json=analysis_bundle["bundle"],
                cost=int(sum(float(item.get("api_cost", 0.0)) for item in analysis_bundle["bundle"]["analysis_reports"]) * 100),
            )
            await self.recorder.store_cio_bundle(
                trace_id=trace_id,
                artifact_type="analysis.bundle",
                payload=analysis_bundle["bundle"],
                source="lead.analysis",
            )
            await self.recorder.emit_event(
                event_callback,
                {
                    "type": "status",
                    "stage": "lead.analysis",
                    "status": "success",
                    "trace_id": trace_id,
                    "workflow_run_id": run_record.uuid,
                    "message": f"分析完成，生成了 {len(analysis_bundle['bundle']['analysis_ids'])} 份分析报告。",
                },
            )

            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name="lead.research_development",
                event_type="start",
                status="running",
                input_json={"domain": request.domain, "analysis_ids": analysis_bundle["bundle"]["analysis_ids"]},
            )
            await self.recorder.emit_event(
                event_callback,
                {
                    "type": "status",
                    "stage": "lead.research_development",
                    "status": "running",
                    "trace_id": trace_id,
                    "workflow_run_id": run_record.uuid,
                    "message": "策划组正在整理标题、提示词和脚本方向。",
                },
            )
            prompt_bundle = await self._run_prompt_bundle(
                trace_id=trace_id,
                request=request,
                domain=request.domain,
                hotspots=selected_hotspots,
                analyses=analysis_bundle["analysis_reports"],
            )
            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name="lead.research_development",
                event_type="finish",
                status="success",
                input_json={"domain": request.domain},
                output_json=prompt_bundle,
            )
            await self.recorder.store_cio_bundle(
                trace_id=trace_id,
                artifact_type="prompt.bundle",
                payload=prompt_bundle,
                source="lead.research_development",
            )
            await self.recorder.emit_event(
                event_callback,
                {
                    "type": "status",
                    "stage": "lead.research_development",
                    "status": "success",
                    "trace_id": trace_id,
                    "workflow_run_id": run_record.uuid,
                    "message": "策划完成，已经整理出提示词包和候选标题。",
                },
            )

            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name="lead.production",
                event_type="start",
                status="running",
                input_json={"prompt_bundle": prompt_bundle},
            )
            await self.recorder.emit_event(
                event_callback,
                {
                    "type": "status",
                    "stage": "lead.production",
                    "status": "running",
                    "trace_id": trace_id,
                    "workflow_run_id": run_record.uuid,
                    "message": "制作组正在生成脚本，并按条件尝试出视频。",
                },
            )
            production_bundle = await self._run_production(
                trace_id=trace_id,
                request=request,
                prompt_bundle=prompt_bundle,
                primary_analysis=analysis_bundle["analysis_reports"][0],
            )
            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name="lead.production",
                event_type="finish",
                status="success",
                input_json={"prompt_bundle": prompt_bundle},
                output_json=production_bundle["trace_bundle"],
            )
            await self.recorder.store_cio_bundle(
                trace_id=trace_id,
                artifact_type="production.bundle",
                payload=production_bundle["trace_bundle"],
                source="lead.production",
            )
            await self.recorder.emit_event(
                event_callback,
                {
                    "type": "status",
                    "stage": "lead.production",
                    "status": "success",
                    "trace_id": trace_id,
                    "workflow_run_id": run_record.uuid,
                    "message": "制作完成，脚本已落地，视频产物也已进入结果包。",
                },
            )

            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name="lead.qa",
                event_type="start",
                status="running",
                input_json={
                    "production_bundle": production_bundle["trace_bundle"],
                    "analysis_bundle": analysis_bundle["bundle"],
                },
            )
            await self.recorder.emit_event(
                event_callback,
                {
                    "type": "status",
                    "stage": "lead.qa",
                    "status": "running",
                    "trace_id": trace_id,
                    "workflow_run_id": run_record.uuid,
                    "message": "质检组正在检查画面质量、合规性与技术参数。",
                },
            )
            qa_bundle = await self._run_qa(
                trace_id=trace_id,
                request=request,
                prompt_bundle=prompt_bundle,
                analysis_bundle=analysis_bundle["bundle"],
                production_bundle=production_bundle["bundle"],
            )
            if not qa_bundle["qa_report"]["pass"] and qa_bundle["qa_report"]["retry_recommended"]:
                reroute_target = qa_bundle["qa_report"].get("reroute_target") or self.assembly.control_plane.get_qa_reroute_mapping().get(
                    "retry_production",
                    "lead.production",
                )
                reroute_label = "策划组" if reroute_target == "lead.research_development" else "制作组"
                if reroute_target == "lead.research_development":
                    await self.recorder.record_stage(
                        trace_id=trace_id,
                        skill_name="lead.research_development",
                        event_type="rework",
                        status="running",
                        input_json={"qa_feedback": qa_bundle["qa_report"]["recommendation"]},
                    )
                    prompt_bundle = await self._run_prompt_bundle(
                        trace_id=trace_id,
                        request=request,
                        domain=request.domain,
                        hotspots=selected_hotspots,
                        analyses=analysis_bundle["analysis_reports"],
                    )
                    await self.recorder.record_stage(
                        trace_id=trace_id,
                        skill_name="lead.research_development",
                        event_type="rework_finish",
                        status="success",
                        output_json=prompt_bundle,
                    )
                await self.recorder.record_stage(
                    trace_id=trace_id,
                    skill_name="lead.production",
                    event_type="rework",
                    status="running",
                    input_json={"qa_feedback": qa_bundle["qa_report"]["recommendation"]},
                )
                await self.recorder.emit_event(
                    event_callback,
                    {
                        "type": "status",
                        "stage": "lead.qa",
                        "status": "failed",
                        "trace_id": trace_id,
                        "workflow_run_id": run_record.uuid,
                        "message": f"质检未通过，已打回{reroute_label}进行一次返工。",
                    },
                )
                production_bundle = await self._run_production(
                    trace_id=trace_id,
                    request=request,
                    prompt_bundle=prompt_bundle,
                    primary_analysis=analysis_bundle["analysis_reports"][0],
                    qa_feedback=qa_bundle["qa_report"]["recommendation"],
                )
                await self.recorder.record_stage(
                    trace_id=trace_id,
                    skill_name="lead.production",
                    event_type="rework_finish",
                    status="success",
                    output_json=production_bundle["trace_bundle"],
                )
                await self.recorder.record_stage(
                    trace_id=trace_id,
                    skill_name="lead.qa",
                    event_type="recheck",
                    status="running",
                    input_json={"production_bundle": production_bundle["trace_bundle"]},
                )
                qa_bundle = await self._run_qa(
                    trace_id=trace_id,
                    request=request,
                    prompt_bundle=prompt_bundle,
                    analysis_bundle=analysis_bundle["bundle"],
                    production_bundle=production_bundle["bundle"],
                )
            qa_status = "success" if qa_bundle["qa_report"]["pass"] else "failed"
            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name="lead.qa",
                event_type="finish",
                status=qa_status,
                input_json={"production_bundle": production_bundle["trace_bundle"]},
                output_json=qa_bundle["bundle"],
            )
            await self.recorder.store_cio_bundle(
                trace_id=trace_id,
                artifact_type="qa.bundle",
                payload=qa_bundle["bundle"],
                source="lead.qa",
            )
            await self.recorder.emit_event(
                event_callback,
                {
                    "type": "status",
                    "stage": "lead.qa",
                    "status": qa_status,
                    "trace_id": trace_id,
                    "workflow_run_id": run_record.uuid,
                    "message": "质检通过，可以进入发布组。" if qa_bundle["qa_report"]["pass"] else "质检未通过，本次流水线已被拦截。",
                },
            )
            if not qa_bundle["qa_report"]["pass"]:
                raise ValueError(qa_bundle["qa_report"]["recommendation"])

            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name="lead.publish",
                event_type="start",
                status="running",
                input_json={
                    "production_bundle": production_bundle["bundle"],
                    "qa_bundle": qa_bundle["bundle"],
                },
            )
            await self.recorder.emit_event(
                event_callback,
                {
                    "type": "status",
                    "stage": "lead.publish",
                    "status": "running",
                    "trace_id": trace_id,
                    "workflow_run_id": run_record.uuid,
                    "message": "发布组正在整理投放计划和交付结果。",
                },
            )
            publish_bundle = await self._run_publish(
                trace_id=trace_id,
                request=request,
                production_bundle=production_bundle,
                qa_bundle=qa_bundle,
            )
            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name="lead.publish",
                event_type="finish",
                status="success",
                input_json={
                    "production_bundle": production_bundle["bundle"],
                    "qa_bundle": qa_bundle["bundle"],
                },
                output_json=publish_bundle["bundle"],
            )
            await self.recorder.store_cio_bundle(
                trace_id=trace_id,
                artifact_type="publish.bundle",
                payload=publish_bundle["bundle"],
                source="lead.publish",
            )
            await self.recorder.emit_event(
                event_callback,
                {
                    "type": "status",
                    "stage": "lead.publish",
                    "status": "success",
                    "trace_id": trace_id,
                    "workflow_run_id": run_record.uuid,
                    "message": "发布阶段完成，CEO 正在整理最终报告。",
                },
            )

            workflow_notes = [
                f"start_event={start_event.event_id}",
                *finance_bundle["notes"],
                *research_bundle["notes"],
                *analysis_bundle["notes"],
                *production_bundle["notes"],
                *qa_bundle["notes"],
                *publish_bundle["notes"],
            ]
            selected_hotspots = research_bundle["selected_hotspots"]
            analysis_ids = analysis_bundle["bundle"]["analysis_ids"]
            prompt_package_payload = {
                **prompt_bundle["prompt_package"],
                "selected_hotspot_ids": [item["uuid"] for item in selected_hotspots],
            }
            script_obj = production_bundle["script"]
            video_task_obj = production_bundle["video_task"]
            render_bundle = production_bundle["bundle"].get("render_bundle") if "bundle" in production_bundle else production_bundle.get("render_bundle")
            delivery_asset_url = (
                video_task_obj.video_url
                if video_task_obj and getattr(video_task_obj, "video_url", None)
                else (render_bundle or {}).get("delivery_asset_url")
            )
            result_payload = {
                "trace_id": trace_id,
                "domain": request.domain,
                "platform": request.platform,
                "finance_bundle": finance_bundle,
                "expanded_queries": expanded_queries,
                "selected_hotspots": selected_hotspots,
                "prompt_package": prompt_package_payload,
                "analysis_ids": analysis_ids,
                "script_id": script_obj.uuid,
                "script_status": script_obj.status,
                "qa_status": qa_bundle["qa_report"]["qa_status"],
                "video_task_id": video_task_obj.uuid if video_task_obj else None,
                "video_status": video_task_obj.status if video_task_obj else None,
                "video_url": delivery_asset_url,
                "workflow_notes": workflow_notes,
                "workflow_run_id": run_record.uuid,
                "ceo_plan": ceo_plan.run_plan,
                "lead_route_list": ceo_plan.lead_route_list,
                "research_bundle": research_bundle["bundle"],
                "analysis_bundle": analysis_bundle["bundle"],
                "prompt_bundle": prompt_bundle,
                "production_bundle": production_bundle["trace_bundle"],
                "qa_bundle": qa_bundle["bundle"],
                "publish_bundle": publish_bundle["bundle"],
            }
            await self.assembly.workflow_run_service.mark_completed(
                run_record,
                expanded_queries=expanded_queries,
                selected_hotspot_ids=[item["uuid"] for item in selected_hotspots],
                prompt_package=prompt_package_payload,
                analysis_ids=analysis_ids,
                script_id=script_obj.uuid,
                video_task_id=video_task_obj.uuid if video_task_obj else None,
                result_payload=result_payload,
            )
            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name=self.assembly.ceo_skill.skill_name,
                event_type="finish",
                status="success",
                input_json=request_bundle,
                output_json=result_payload,
            )
            return result_payload
        except Exception as exc:
            await self.recorder.record_stage(
                trace_id=trace_id,
                skill_name=self.assembly.ceo_skill.skill_name,
                event_type="fail",
                status="failed",
                input_json=request_bundle,
                error_message=str(exc),
            )
            await self.assembly.workflow_run_service.mark_failed(run_record, error_message=str(exc))
            raise

    async def _run_finance_gate(self, *, trace_id: str, workflow_run_id: str, request: DomainWorkflowRequest) -> dict[str, Any]:
        finance_summary = await self.assembly.finance_service.build_summary()
        estimate = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.cfo",
                skill=self.assembly.cfo_estimate_skill,
                input_bundle={"trace_id": trace_id, **request.model_dump()},
            )
        ).output_json["finance_estimate"]
        finance_check = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.cfo",
                skill=self.assembly.cfo_verify_skill,
                input_bundle={
                    "estimated_cost": estimate["estimated_cost"],
                    "required_services": estimate["required_services"],
                    **finance_summary,
                },
            )
        ).output_json["finance_check"]
        if not finance_check["passed"]:
            reasons = finance_check.get("blocked_reasons") or [finance_check.get("message") or "finance gate blocked"]
            raise ValueError(f"finance gate blocked: {'; '.join(str(item) for item in reasons)}")
        receipt = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.cfo",
                skill=self.assembly.cfo_charge_skill,
                input_bundle={
                    "trace_id": trace_id,
                    "workflow_run_id": workflow_run_id,
                    "estimated_cost": estimate["estimated_cost"],
                    "currency": estimate["currency"],
                    "request_summary": (request.publish_goal or request.domain)[:200],
                    "metadata": {
                        "platform": request.platform,
                        "duration": request.duration,
                        "estimated_tokens": estimate["estimated_tokens"],
                        "required_services": estimate["required_services"],
                    },
                },
                method_name="async_execute",
            )
        ).output_json["receipt"]
        return {
            "finance_estimate": estimate,
            "finance_check": finance_check,
            "receipt": receipt,
            "notes": [f"finance_reserved={receipt['amount']}", f"finance_tx={receipt['transaction_id']}"],
        }

    async def _run_research(self, *, trace_id: str, request: DomainWorkflowRequest, expanded_queries: list[str]) -> dict[str, Any]:
        per_query = max(1, request.hotspot_count // max(len(expanded_queries), 1))
        collected: list[dict[str, Any]] = []
        for query in expanded_queries:
            items = await self.assembly.hotspot_service.fetch_hotspots(
                HotspotFetchRequest(platform=request.platform, keyword=query, count=per_query + 1)
            )
            collected.extend(self.assembly.serialize_hotspot(item) for item in items)

        collected_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research",
                skill=self.assembly.hotspot_collection_skill,
                input_bundle={"trace_id": trace_id, "hotspots": collected},
            )
        ).output_json
        dedup_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research",
                skill=self.assembly.hotspot_dedup_skill,
                input_bundle={"trace_id": trace_id, "hotspots": collected_bundle["hotspots"]},
            )
        ).output_json
        ranked_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research",
                skill=self.assembly.hotspot_ranking_skill,
                input_bundle={"trace_id": trace_id, "hotspots": dedup_bundle["hotspots"]},
            )
        ).output_json
        selected_hotspots = [item for item in ranked_bundle["hotspots"][: request.top_n]]
        snapshot_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research",
                skill=self.assembly.hotspot_snapshot_skill,
                input_bundle={
                    "trace_id": trace_id,
                    "domain": request.domain,
                    "expanded_queries": expanded_queries,
                    "selected_hotspots": selected_hotspots,
                    "hotspot_pool": ranked_bundle["hotspots"],
                },
            )
        ).output_json
        return {
            "bundle": {
                "expanded_queries": expanded_queries,
                "hotspot_pool": ranked_bundle["hotspots"],
                "selected_hotspots": selected_hotspots,
                "snapshot": snapshot_bundle["hotspot_bundle"],
            },
            "selected_hotspots": selected_hotspots,
            "notes": [f"research_selected={len(selected_hotspots)}"],
        }

    async def _run_analysis(self, *, trace_id: str, hotspots: list[dict[str, Any]]) -> dict[str, Any]:
        analysis_reports: list[AnalysisReport] = []
        analysis_bundles: list[dict[str, Any]] = []
        for hotspot_data in hotspots:
            hotspot = await self.assembly.load_hotspot(hotspot_data["uuid"])
            report = await self.assembly.analysis_service.analyze_content(hotspot)
            analysis_reports.append(report)
            base_bundle = self.assembly.serialize_analysis(report)
            structured_bundle = (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.analysis",
                    skill=self.assembly.hotspot_structure_skill,
                    input_bundle=base_bundle,
                )
            ).output_json
            hook_bundle = (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.analysis",
                    skill=self.assembly.hook_extraction_skill,
                    input_bundle=structured_bundle,
                )
            ).output_json
            emotion_bundle = (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.analysis",
                    skill=self.assembly.emotion_curve_skill,
                    input_bundle=hook_bundle,
                )
            ).output_json
            risk_bundle = (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.analysis",
                    skill=self.assembly.risk_extraction_skill,
                    input_bundle=emotion_bundle,
                )
            ).output_json
            reusable_bundle = (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.analysis",
                    skill=self.assembly.reusable_element_skill,
                    input_bundle=risk_bundle,
                )
            ).output_json
            persisted_bundle = (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.analysis",
                    skill=self.assembly.analysis_persist_skill,
                    input_bundle={"trace_id": trace_id, **reusable_bundle, "analysis_id": report.uuid},
                )
            ).output_json
            analysis_bundles.append(persisted_bundle["analysis_bundle"])
        return {
            "bundle": {
                "analysis_reports": analysis_bundles,
                "analysis_ids": [report.uuid for report in analysis_reports],
            },
            "analysis_reports": analysis_reports,
            "notes": [f"analysis_count={len(analysis_reports)}"],
        }

    async def _run_prompt_bundle(
        self,
        *,
        trace_id: str,
        request: DomainWorkflowRequest,
        domain: str,
        hotspots: list[dict[str, Any]],
        analyses: list[AnalysisReport],
    ) -> dict[str, Any]:
        prompt_package = self.assembly.trend_service.build_prompt_package(
            domain=domain,
            hotspots=[self.assembly.load_hotspot_sync(item) for item in hotspots],
            analyses=analyses,
            style=request.style,
            content_type=request.content_type,
            audience=request.audience,
            publish_goal=request.publish_goal,
        )
        prompt_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research_development",
                skill=self.assembly.prompt_package_skill,
                input_bundle={"trace_id": trace_id, **prompt_package},
            )
        ).output_json
        title_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research_development",
                skill=self.assembly.title_candidate_skill,
                input_bundle={"trace_id": trace_id, **prompt_bundle["prompt_bundle"]},
            )
        ).output_json
        validation_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research_development",
                skill=self.assembly.prompt_validation_skill,
                input_bundle={"trace_id": trace_id, **prompt_bundle["prompt_bundle"], **title_bundle},
            )
        ).output_json
        version_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research_development",
                skill=self.assembly.prompt_version_skill,
                input_bundle={"trace_id": trace_id, **validation_bundle},
            )
        ).output_json
        return {
            "trace_id": trace_id,
            "prompt_package": prompt_package,
            "prompt_bundle": prompt_bundle["prompt_bundle"],
            "title_candidates": title_bundle.get("title_candidates", []),
            "validation": validation_bundle,
            "version": version_bundle.get("version", 1),
            "version_bundle": version_bundle,
        }

    async def _run_production(
        self,
        *,
        trace_id: str,
        request: DomainWorkflowRequest,
        prompt_bundle: dict[str, Any],
        primary_analysis: AnalysisReport,
        qa_feedback: str | None = None,
    ) -> dict[str, Any]:
        topic = prompt_bundle["prompt_bundle"]["script_topic"]
        if qa_feedback:
            topic = f"{topic} | QA修正：{qa_feedback[:80]}"
        script = await self.assembly.script_service.generate_script(
            analysis=primary_analysis,
            content_type=request.content_type,
            style=request.style,
            topic=topic,
            duration=request.duration,
        )
        script_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.production",
                skill=self.assembly.script_draft_skill,
                input_bundle={"trace_id": trace_id, "script": self.assembly.serialize_script(script)},
            )
        ).output_json
        material_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research",
                skill=self.assembly.material_search_skill,
                input_bundle={
                    "trace_id": trace_id,
                    "platform": request.platform,
                    "target_duration": request.duration,
                    "search_terms": list(prompt_bundle["prompt_bundle"].get("visual_keywords", [])),
                    "scenes": list(script.scenes or []),
                },
            )
        ).output_json
        subtitle_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.production",
                skill=self.assembly.subtitle_compose_skill,
                input_bundle={
                    "trace_id": trace_id,
                    "script": self.assembly.serialize_script(script),
                    "target_duration": request.duration,
                },
            )
        ).output_json
        voiceover_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.production",
                skill=self.assembly.voiceover_generate_skill,
                input_bundle={
                    "trace_id": trace_id,
                    "script": self.assembly.serialize_script(script),
                    "target_duration": request.duration,
                    "voice_profile": "narrator-neutral",
                },
            )
        ).output_json
        workflow_notes: list[str] = []
        if request.auto_approve_script:
            script = await self.assembly.script_service.review_script(script.uuid, True, "Auto-approved by skill workflow.")
            script_bundle = (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.production",
                    skill=self.assembly.script_review_skill,
                    input_bundle={"trace_id": trace_id, "script": self.assembly.serialize_script(script)},
                )
            ).output_json
            workflow_notes.append("script_approved")

        video_task = None
        if request.auto_generate_video:
            if script.status != "approved":
                workflow_notes.append("video_skipped_unapproved_script")
            else:
                video_task = await self.assembly.video_service.create_task(script=script, style=request.video_style or request.style)
                video_task = await self.assembly.video_service.process_task(video_task.uuid)
                video_task_bundle = (
                    await self.recorder.call_skill(
                        trace_id=trace_id,
                        parent_id="lead.production",
                        skill=self.assembly.video_task_skill,
                        input_bundle={"trace_id": trace_id, "video_task": self.assembly.serialize_video_task(video_task)},
                    )
                ).output_json
                processed_bundle = (
                    await self.recorder.call_skill(
                        trace_id=trace_id,
                        parent_id="lead.production",
                        skill=self.assembly.video_process_skill,
                        input_bundle={"trace_id": trace_id, **video_task_bundle},
                    )
                ).output_json
                review_bundle = (
                    await self.recorder.call_skill(
                        trace_id=trace_id,
                        parent_id="lead.production",
                        skill=self.assembly.video_review_skill,
                        input_bundle={"trace_id": trace_id, **processed_bundle},
                    )
                ).output_json
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.production",
                    skill=self.assembly.asset_storage_skill,
                    input_bundle={
                        "trace_id": trace_id,
                        **review_bundle,
                        "video_bundle": {
                            "subtitle_bundle": subtitle_bundle,
                            "voiceover_bundle": voiceover_bundle,
                            "material_bundle": material_bundle,
                        },
                    },
                )
                workflow_notes.append("video_generated")
        else:
            workflow_notes.append("video_not_requested")
        composition_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.production",
                skill=self.assembly.video_compose_plan_skill,
                input_bundle={
                    "platform": request.platform,
                    "script": self.assembly.serialize_script(script),
                    "material_bundle": material_bundle,
                    "subtitle_bundle": subtitle_bundle,
                    "voiceover_bundle": voiceover_bundle,
                    "video_task": self.assembly.serialize_video_task(video_task) if video_task else None,
                },
            )
        ).output_json
        render_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.production",
                skill=self.assembly.render_execute_skill,
                input_bundle={
                    "trace_id": trace_id,
                    "platform": request.platform,
                    "duration": request.duration,
                    "composition_bundle": composition_bundle,
                    "video_task": self.assembly.serialize_video_task(video_task) if video_task else None,
                },
            )
        ).output_json
        await self.recorder.call_skill(
            trace_id=trace_id,
            parent_id="lead.production",
            skill=self.assembly.asset_storage_skill,
            input_bundle={
                "trace_id": trace_id,
                "video_bundle": {
                    "subtitle_bundle": subtitle_bundle,
                    "voiceover_bundle": voiceover_bundle,
                    "material_bundle": material_bundle,
                    "composition_bundle": composition_bundle,
                    "render_bundle": render_bundle,
                },
            },
        )
        if render_bundle.get("render_mode") == "ffmpeg_preview":
            workflow_notes.append("scene_preview_rendered")
        elif render_bundle.get("render_mode") == "preview_placeholder":
            workflow_notes.append("placeholder_preview_rendered")
        if qa_feedback:
            workflow_notes.append("qa_rework_requested")
        production_bundle = {
            "script": script,
            "video_task": video_task,
            "script_bundle": script_bundle,
            "material_bundle": material_bundle,
            "subtitle_bundle": subtitle_bundle,
            "voiceover_bundle": voiceover_bundle,
            "composition_bundle": composition_bundle,
            "render_bundle": render_bundle,
            "qa_feedback": qa_feedback,
            "notes": workflow_notes,
        }
        if (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.production",
                skill=self.assembly.production_retry_skill,
                input_bundle={"trace_id": trace_id, **production_bundle},
            )
        ).output_json["retry"]:
            workflow_notes.append("production_retry_requested")
        return {
            "bundle": production_bundle,
            "trace_bundle": {
                "script": self.assembly.serialize_script(script),
                "video_task": self.assembly.serialize_video_task(video_task) if video_task else None,
                "script_bundle": script_bundle,
                "material_bundle": material_bundle,
                "subtitle_bundle": subtitle_bundle,
                "voiceover_bundle": voiceover_bundle,
                "composition_bundle": composition_bundle,
                "render_bundle": render_bundle,
                "qa_feedback": qa_feedback,
                "notes": workflow_notes,
            },
            "script": script,
            "video_task": video_task,
            "notes": workflow_notes,
        }

    async def _run_qa(
        self,
        *,
        trace_id: str,
        request: DomainWorkflowRequest,
        prompt_bundle: dict[str, Any],
        analysis_bundle: dict[str, Any],
        production_bundle: dict[str, Any],
    ) -> dict[str, Any]:
        script = production_bundle["script"]
        video_task = production_bundle.get("video_task")
        serialized_script = self.assembly.serialize_script(script)
        serialized_video_task = self.assembly.serialize_video_task(video_task) if video_task else None
        checks = []
        checks.append(
            (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.qa",
                    skill=self.assembly.video_quality_check_skill,
                    input_bundle={"trace_id": trace_id, "platform": request.platform, "video_task": serialized_video_task},
                )
            ).output_json
        )
        checks.append(
            (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.qa",
                    skill=self.assembly.content_compliance_check_skill,
                    input_bundle={
                        "trace_id": trace_id,
                        "platform": request.platform,
                        "script": serialized_script,
                        "video_task": serialized_video_task,
                    },
                )
            ).output_json
        )
        checks.append(
            (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.qa",
                    skill=self.assembly.gene_alignment_check_skill,
                    input_bundle={
                        "trace_id": trace_id,
                        "script": serialized_script,
                        "analysis_bundle": analysis_bundle,
                        "prompt_bundle": prompt_bundle,
                    },
                )
            ).output_json
        )
        checks.append(
            (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.qa",
                    skill=self.assembly.technical_spec_check_skill,
                    input_bundle={
                        "trace_id": trace_id,
                        "platform": request.platform,
                        "script": serialized_script,
                        "video_task": serialized_video_task,
                    },
                )
            ).output_json
        )
        checks.append(
            (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.qa",
                    skill=self.assembly.delivery_asset_check_skill,
                    input_bundle={
                        "trace_id": trace_id,
                        "script": serialized_script,
                        "material_bundle": production_bundle.get("material_bundle") or {},
                        "subtitle_bundle": production_bundle.get("subtitle_bundle") or {},
                        "voiceover_bundle": production_bundle.get("voiceover_bundle") or {},
                        "composition_bundle": production_bundle.get("composition_bundle") or {},
                    },
                )
            ).output_json
        )
        checks.append(
            (
                await self.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.qa",
                    skill=self.assembly.render_output_check_skill,
                    input_bundle={
                        "trace_id": trace_id,
                        "platform": request.platform,
                        "render_bundle": production_bundle.get("render_bundle") or {},
                    },
                )
            ).output_json
        )
        qa_report = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.qa",
                skill=self.assembly.qa_report_skill,
                input_bundle={"trace_id": trace_id, "checks": checks, "video_task": serialized_video_task},
            )
        ).output_json["qa_report"]
        if video_task:
            video_task.quality_score = qa_report["overall_score"]
            video_task.quality_report = jsonable_encoder({"checks": checks, "qa_report": qa_report, "trace_id": trace_id})
            await self.assembly.session.flush()
        return {
            "bundle": {
                "checks": checks,
                "qa_report": qa_report,
                "video_task": self.assembly.serialize_video_task(video_task) if video_task else None,
            },
            "qa_report": qa_report,
            "notes": [f"qa_status={qa_report['qa_status']}"],
        }

    async def _run_publish(
        self,
        *,
        trace_id: str,
        request: DomainWorkflowRequest,
        production_bundle: dict[str, Any],
        qa_bundle: dict[str, Any],
    ) -> dict[str, Any]:
        video_task = production_bundle.get("video_task")
        render_bundle = production_bundle.get("render_bundle") or {}
        delivery_asset_url = (
            video_task.video_url
            if video_task and getattr(video_task, "video_url", None)
            else render_bundle.get("delivery_asset_url")
        )
        plan = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.publish",
                skill=self.assembly.publish_plan_skill,
                input_bundle={
                    "trace_id": trace_id,
                    "platform": request.platform,
                    "publish_goal": request.publish_goal,
                    "audience": request.audience,
                    "video_url": delivery_asset_url,
                    "video_task_id": video_task.uuid if video_task else None,
                    "qa_status": qa_bundle["qa_report"]["qa_status"],
                },
            )
        ).output_json["publish_plan"]
        platform_payload = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.publish",
                skill=self.assembly.platform_adapter_skill,
                input_bundle={"trace_id": trace_id, "publish_plan": plan},
            )
        ).output_json
        publish_result = self.assembly.publish_service.execute_publish(
            {"trace_id": trace_id, "publish_plan": plan, "platform_payload": platform_payload["platform_payload"]}
        )
        publish_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.publish",
                skill=self.assembly.publish_execute_skill,
                input_bundle={"trace_id": trace_id, "publish_result": publish_result},
            )
        ).output_json
        callback_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.publish",
                skill=self.assembly.publish_callback_skill,
                input_bundle={"trace_id": trace_id, **publish_bundle},
            )
        ).output_json
        history_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.publish",
                skill=self.assembly.publish_history_skill,
                input_bundle={"trace_id": trace_id, **callback_bundle},
            )
        ).output_json
        retry_bundle = (
            await self.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.publish",
                skill=self.assembly.publish_retry_skill,
                input_bundle={"trace_id": trace_id, **history_bundle},
            )
        ).output_json
        return {
            "bundle": {
                "publish_plan": plan,
                "platform_payload": platform_payload["platform_payload"],
                "publish_result": publish_result,
                "callback": callback_bundle,
                "history": history_bundle,
                "retry": retry_bundle,
            },
            "notes": [f"publish_status={publish_result.get('status', 'unknown')}"],
        }
