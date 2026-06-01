from __future__ import annotations

from departments.CIO.schemas.video import DomainWorkflowRequest


class PublishDeliveryUseCase:
    """CAO use case for publish planning, platform adaptation, callbacks, and history."""

    def __init__(self, assembly) -> None:
        self.assembly = assembly

    async def execute(
        self,
        *,
        trace_id: str,
        request: DomainWorkflowRequest,
        production_bundle: dict,
        qa_bundle: dict,
    ) -> dict:
        video_task = production_bundle.get("video_task")
        render_bundle = production_bundle.get("render_bundle") or {}
        delivery_asset_url = (
            video_task.video_url
            if video_task and getattr(video_task, "video_url", None)
            else render_bundle.get("delivery_asset_url")
        )
        plan = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.publish",
                skill=self.assembly.get_skill("lead.publish.publish_plan"),
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
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.publish",
                skill=self.assembly.get_skill("lead.publish.platform_adapter"),
                input_bundle={"trace_id": trace_id, "publish_plan": plan},
            )
        ).output_json["platform_payload"]
        publish_result = self.assembly.publish_service.execute_publish(
            {"trace_id": trace_id, "publish_plan": plan, "platform_payload": platform_payload}
        )
        publish_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.publish",
                skill=self.assembly.get_skill("lead.publish.publish_execute"),
                input_bundle={"trace_id": trace_id, "publish_result": publish_result},
            )
        ).output_json
        callback_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.publish",
                skill=self.assembly.get_skill("lead.publish.publish_callback"),
                input_bundle={"trace_id": trace_id, **publish_bundle},
            )
        ).output_json
        history_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.publish",
                skill=self.assembly.get_skill("lead.publish.publish_history"),
                input_bundle={"trace_id": trace_id, **callback_bundle},
            )
        ).output_json
        retry_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.publish",
                skill=self.assembly.get_skill("lead.publish.retry_recovery"),
                input_bundle={"trace_id": trace_id, **history_bundle},
            )
        ).output_json
        return {
            "bundle": {
                "publish_plan": plan,
                "platform_payload": platform_payload,
                "publish_result": publish_result,
                "callback": callback_bundle,
                "history": history_bundle,
                "retry": retry_bundle,
            },
            "notes": [f"publish_status={publish_result.get('status', 'unknown')}"],
        }
