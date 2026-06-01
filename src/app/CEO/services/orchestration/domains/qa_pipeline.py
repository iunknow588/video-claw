from __future__ import annotations

from app.CEO.services.orchestration.pipeline import PipelineContext, PipelineResult
from app.CQO.services.use_cases.quality_gate import QualityGateUseCase


class QAPipeline:
    """CEO-owned orchestration wrapper for the CQO quality gate."""

    def __init__(self, assembly) -> None:
        self.use_case = QualityGateUseCase(assembly)

    async def run(self, context: PipelineContext, input_bundle: dict[str, object]) -> PipelineResult:
        payload = await self.use_case.execute(
            trace_id=context.trace_id,
            request=context.request,
            prompt_bundle=input_bundle["prompt_bundle"],
            analysis_bundle=input_bundle["analysis_bundle"],
            production_bundle=input_bundle["production_bundle"],
        )
        status = "success" if payload["qa_report"]["qa_status"] == "passed" else "rework"
        return PipelineResult.from_payload(payload, status=status)
