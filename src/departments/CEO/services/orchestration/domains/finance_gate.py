from __future__ import annotations

from departments.CEO.services.orchestration.pipeline import PipelineContext, PipelineResult
from departments.CFO.services.use_cases.finance_gate import FinanceGateUseCase


class FinanceGate:
    """CEO-owned orchestration wrapper for the CFO finance gate."""

    def __init__(self, assembly) -> None:
        self.use_case = FinanceGateUseCase(assembly)

    async def run(self, context: PipelineContext, input_bundle: dict[str, object]) -> PipelineResult:
        payload = await self.use_case.execute(
            trace_id=context.trace_id,
            workflow_run_id=context.workflow_run_id,
            request=context.request,
        )
        return PipelineResult.from_payload(payload)
