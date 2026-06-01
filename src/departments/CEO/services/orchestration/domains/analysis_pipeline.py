from __future__ import annotations

from departments.CCO.services.use_cases.content_analysis import ContentAnalysisUseCase
from departments.CEO.services.orchestration.pipeline import PipelineContext, PipelineResult


class AnalysisPipeline:
    """CEO-owned orchestration wrapper for the CCO analysis pipeline."""

    def __init__(self, assembly) -> None:
        self.use_case = ContentAnalysisUseCase(assembly)

    async def run(self, context: PipelineContext, input_bundle: dict[str, object]) -> PipelineResult:
        payload = await self.use_case.execute(trace_id=context.trace_id, hotspots=input_bundle["hotspots"])
        return PipelineResult.from_payload(payload)
