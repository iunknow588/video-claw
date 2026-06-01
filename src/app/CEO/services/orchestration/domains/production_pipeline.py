from __future__ import annotations

from app.CEO.services.orchestration.pipeline import PipelineContext, PipelineResult
from app.COO.services.use_cases.video_production import VideoProductionUseCase


class ProductionPipeline:
    """CEO-owned orchestration wrapper for the COO production pipeline."""

    def __init__(self, assembly) -> None:
        self.use_case = VideoProductionUseCase(assembly)

    async def run(self, context: PipelineContext, input_bundle: dict[str, object]) -> PipelineResult:
        payload = await self.use_case.execute(
            trace_id=context.trace_id,
            request=context.request,
            planning_bundle=input_bundle["planning_bundle"],
            primary_analysis=input_bundle["primary_analysis"],
            qa_feedback=input_bundle.get("qa_feedback"),
        )
        return PipelineResult.from_payload(payload)
