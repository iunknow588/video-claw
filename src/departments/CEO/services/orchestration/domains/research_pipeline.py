from __future__ import annotations

from departments.CEO.services.orchestration.pipeline import PipelineContext, PipelineResult
from departments.CSO.services.use_cases.research import ResearchUseCase


class ResearchPipeline:
    """CEO-owned orchestration wrapper for the CSO research pipeline."""

    def __init__(self, assembly) -> None:
        self.use_case = ResearchUseCase(assembly)

    async def run(self, context: PipelineContext, input_bundle: dict[str, object]) -> PipelineResult:
        payload = await self.use_case.execute(trace_id=context.trace_id, request=context.request)
        return PipelineResult.from_payload(payload)
