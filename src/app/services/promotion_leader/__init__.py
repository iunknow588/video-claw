from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.CMO.skills import ChatUISkill, ProgressUISkill, ReportUISkill
from app.services.ceo_control import CEOControlService
from app.services.production_pipeline import ProductionPipelineService
from app.schemas.video import DomainWorkflowRequest
from app.services.workflow_runs import WorkflowRunService
from app.services.workflow_steps import WorkflowStepLogService
from app.skills.catalog import SKILL_METADATA_OVERRIDES
from app.skills.runtime import SkillRuntimeManager

PromotionEventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class CMOService:
    """External communication leader that owns UI-facing interaction."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.pipeline_service = ProductionPipelineService(session)
        self.ceo_control_service = CEOControlService(session)
        self.workflow_run_service = WorkflowRunService(session)
        self.workflow_step_service = WorkflowStepLogService(session)
        self.skill_runtime = SkillRuntimeManager()

        self.chat_ui_skill = ChatUISkill()
        self.progress_ui_skill = ProgressUISkill()
        self.report_ui_skill = ReportUISkill()

    async def handle_user_message(
        self,
        message: str,
        *,
        event_callback: PromotionEventCallback | None = None,
    ) -> None:
        parsed = await self._invoke_skill(
            self.chat_ui_skill,
            {"action": "interpret_user_message", "message": message},
        )
        intent = parsed.get("intent")

        if intent == "empty":
            await self._emit_formatted_reply(parsed.get("reply_message", ""), event_callback)
            return

        if intent == "recent_runs":
            await self._emit_formatted_reply(parsed.get("reply_message", ""), event_callback)
            runs = await self.workflow_run_service.list_runs(limit=5)
            report_event = await self._format_report(
                "format_recent_runs",
                runs=jsonable_encoder(runs),
            )
            await self._emit(event_callback, report_event)
            return

        if intent == "trace_request":
            await self._emit_formatted_reply(parsed.get("reply_message", ""), event_callback)
            run_id = parsed.get("run_id")
            run = await self.workflow_run_service.get_by_uuid(run_id)
            if not run:
                error_event = await self._format_report("format_error", message=f"没有找到任务 {run_id}。")
                await self._emit(event_callback, error_event)
                return
            trace_id = getattr(run, "trace_id", None)
            summary = await self.workflow_step_service.summarize_trace(trace_id) if trace_id else {"trace_id": None}
            report_event = await self._format_report(
                "format_trace_report",
                run=jsonable_encoder(run),
                summary=summary,
            )
            await self._emit(event_callback, report_event)
            return

        if intent == "workflow_request":
            workflow_request = DomainWorkflowRequest(**(parsed.get("workflow_request") or {}))
            await self._emit_formatted_reply(parsed.get("reply_message", ""), event_callback)

            async def relay_workflow_event(event: dict[str, Any]) -> None:
                if event.get("type") != "status":
                    await self._emit(event_callback, event)
                    return
                progress_event = await self._invoke_skill(
                    self.progress_ui_skill,
                    {"action": "format_status_event", "event": event},
                )
                await self._emit(event_callback, progress_event["event"])

            try:
                result = await self.pipeline_service.run(workflow_request, event_callback=relay_workflow_event)
            except Exception as exc:
                error_event = await self._format_report("format_error", message=f"任务执行失败：{exc}")
                await self._emit(event_callback, error_event)
                return

            summary = (
                await self.workflow_step_service.summarize_trace(result["trace_id"])
                if result.get("trace_id")
                else {"trace_id": None}
            )
            result_event = await self._format_report(
                "format_workflow_result",
                result=result,
                summary=summary,
            )
            await self._emit(event_callback, result_event)
            return

        if intent == "company_status":
            await self._emit_formatted_reply(parsed.get("reply_message", ""), event_callback)
            status = await self.ceo_control_service.get_company_status()
            await self._emit(
                event_callback,
                await self._format_report("format_company_status", status=status),
            )
            return

        if intent == "workflow_snapshot":
            await self._emit_formatted_reply(parsed.get("reply_message", ""), event_callback)
            workflow = await self.ceo_control_service.get_workflow()
            await self._emit(
                event_callback,
                await self._format_report("format_workflow_snapshot", workflow=workflow["workflow"]),
            )
            return

        if intent == "leader_list":
            await self._emit_formatted_reply(parsed.get("reply_message", ""), event_callback)
            leaders = await self.ceo_control_service.list_leaders()
            message = "当前归属 CEO 管辖的一级 Leader：\n" + "\n".join(
                f"{item['display_name']} | {item['name']} | 成功率 {item.get('metrics', {}).get('success_rate', 0.0) * 100:.1f}%"
                for item in leaders["leaders"]
            )
            await self._emit(event_callback, await self._format_report("format_reply", message=message))
            return

        if intent == "leader_status":
            await self._emit_formatted_reply(parsed.get("reply_message", ""), event_callback)
            leader = await self.ceo_control_service.get_leader_status(parsed.get("leader_name") or "")
            await self._emit(
                event_callback,
                await self._format_report("format_leader_status", leader=leader["leader"]),
            )
            return

        if intent == "leader_report_request":
            await self._emit_formatted_reply(parsed.get("reply_message", ""), event_callback)
            request = await self.ceo_control_service.request_leader_report(parsed.get("leader_name") or "")
            message = (
                f"已向 {request['request']['leader_display_name']} 发出报告请求，"
                f"请求编号：{request['request']['request_id']}。"
            )
            await self._emit(event_callback, await self._format_report("format_reply", message=message))
            return

        if intent == "optimize_request":
            await self._emit_formatted_reply(parsed.get("reply_message", ""), event_callback)
            command = await self.ceo_control_service.issue_optimize_command(
                leader_name=parsed.get("leader_name") or "",
                target_metric=parsed.get("target_metric") or "",
                goal_value=parsed.get("goal_value"),
            )
            await self._emit(
                event_callback,
                await self._format_report("format_optimize_command", command=command["command"]),
            )
            return

        if intent == "enable_evolution":
            await self._emit_formatted_reply(parsed.get("reply_message", ""), event_callback)
            result = await self.ceo_control_service.enable_evolution()
            await self._emit(event_callback, await self._format_report("format_reply", message=result["message"]))
            return

        if intent == "disable_evolution":
            await self._emit_formatted_reply(parsed.get("reply_message", ""), event_callback)
            result = await self.ceo_control_service.disable_evolution()
            await self._emit(event_callback, await self._format_report("format_reply", message=result["message"]))
            return

        if intent == "evolution_cycle":
            await self._emit_formatted_reply(parsed.get("reply_message", ""), event_callback)
            evolution = await self.ceo_control_service.evolution_cycle()
            await self._emit(
                event_callback,
                await self._format_report("format_evolution_report", evolution=evolution),
            )
            return

        await self._emit_formatted_reply(parsed.get("reply_message", ""), event_callback)

    async def _format_report(self, action: str, **payload: Any) -> dict[str, Any]:
        result = await self._invoke_skill(self.report_ui_skill, {"action": action, **payload})
        return result["event"]

    async def _emit_formatted_reply(
        self,
        message: str,
        event_callback: PromotionEventCallback | None,
    ) -> None:
        reply_event = await self._format_report("format_reply", message=message)
        await self._emit(event_callback, reply_event)

    async def _invoke_skill(self, skill: Any, payload: dict[str, Any]) -> dict[str, Any]:
        skill_name = getattr(skill, "skill_name", None) or getattr(skill, "name", None) or skill.__class__.__name__
        invocation = await self.skill_runtime.invoke(
            skill,
            payload,
            descriptor_overrides=SKILL_METADATA_OVERRIDES.get(skill_name, {}),
        )
        return invocation.output_json

    async def _emit(self, callback: PromotionEventCallback | None, event: dict[str, Any]) -> None:
        if not callback:
            return
        maybe_awaitable = callback(event)
        if inspect.isawaitable(maybe_awaitable):
            await maybe_awaitable


PromotionLeaderService = CMOService
