from __future__ import annotations

from departments.CEO.services.orchestration.pipeline import PipelineContext, PipelineResult
from departments.CTO.services.use_cases.prompt_planning import PromptPlanningUseCase


class RDPipeline:
    """CEO-owned orchestration wrapper for the CTO planning pipeline."""

    def __init__(self, assembly) -> None:
        self.use_case = PromptPlanningUseCase(assembly)

    async def run(self, context: PipelineContext, input_bundle: dict[str, object]) -> PipelineResult:
        payload = await self.use_case.execute(
            trace_id=context.trace_id,
            request=context.request,
            domain=context.request.domain,
            hotspots=input_bundle["hotspots"],
            analyses=input_bundle["analyses"],
        )
        return PipelineResult.from_payload(payload)
