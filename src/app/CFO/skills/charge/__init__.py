from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.CQO.services.audit import AuditService
from app.CEO.skills.base import BaseSkill


class ChargeSkill(BaseSkill):
    skill_name = "lead.cfo.charge"
    description = "Records the CFO reservation/charge receipt and returns a transaction voucher."
    parameters_schema = {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "workflow_run_id": {"type": "string"},
            "estimated_cost": {"type": "number"},
            "currency": {"type": "string"},
            "request_summary": {"type": "string"},
            "metadata": {"type": "object"},
        },
        "required": ["trace_id", "workflow_run_id", "estimated_cost"],
    }
    tags = ["lead", "cfo", "finance", "gate"]
    dependencies = ["lead.cfo.estimate_cost", "lead.cfo.verify_balance"]
    required_tokens = ["request_summary"]

    def __init__(self, session: AsyncSession | None = None, config: dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        self.session = session

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("lead.cfo.charge must be invoked through async_execute")

    async def async_execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        amount = round(float(input_data.get("estimated_cost") or 0.0), 4)
        currency = str(input_data.get("currency") or "USD")
        trace_id = str(input_data.get("trace_id") or "")
        workflow_run_id = str(input_data.get("workflow_run_id") or trace_id)
        request_summary = str(input_data.get("request_summary") or "")
        metadata = dict(input_data.get("metadata") or {})

        if self.session is None:
            return {
                "receipt": {
                    "transaction_id": f"synthetic-{workflow_run_id}",
                    "source_uuid": workflow_run_id,
                    "amount": amount,
                    "currency": currency,
                    "usage_type": "precharge",
                    "request_summary": request_summary,
                    "metadata": metadata,
                }
            }

        record = await AuditService(self.session).record_cost(
            source_type="finance",
            source_uuid=workflow_run_id,
            provider="cfo",
            model_name="budget-ledger",
            amount=amount,
            currency=currency,
            usage_type="precharge",
            request_summary=request_summary,
            metadata_json={
                "trace_id": trace_id,
                **metadata,
            },
        )
        return {
            "receipt": {
                "transaction_id": record.uuid,
                "source_uuid": workflow_run_id,
                "amount": amount,
                "currency": currency,
                "usage_type": record.usage_type,
                "request_summary": request_summary,
                "metadata": {
                    "trace_id": trace_id,
                    **metadata,
                },
            }
        }
