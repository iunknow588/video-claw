from __future__ import annotations

from departments.CIO.schemas.video import DomainWorkflowRequest


class FinanceGateUseCase:
    """CFO use case for budget estimation, verification, and reservation."""

    def __init__(self, assembly) -> None:
        self.assembly = assembly

    async def execute(self, *, trace_id: str, workflow_run_id: str, request: DomainWorkflowRequest) -> dict:
        finance_summary = await self.assembly.finance_service.build_summary()
        estimate = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.cfo",
                skill=self.assembly.get_skill("lead.cfo.estimate_cost"),
                input_bundle={"trace_id": trace_id, **request.model_dump()},
            )
        ).output_json["finance_estimate"]
        finance_check = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.cfo",
                skill=self.assembly.get_skill("lead.cfo.verify_balance"),
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
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.cfo",
                skill=self.assembly.get_skill("lead.cfo.charge"),
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
