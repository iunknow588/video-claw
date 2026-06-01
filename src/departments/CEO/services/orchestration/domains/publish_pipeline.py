from __future__ import annotations

from departments.CAO.services.use_cases.publish_delivery import PublishDeliveryUseCase
from departments.CEO.services.orchestration.pipeline import PipelineContext, PipelineResult


class PublishPipeline:
    """CEO-owned orchestration wrapper for the CAO publish pipeline."""

    def __init__(self, assembly) -> None:
        self.use_case = PublishDeliveryUseCase(assembly)

    async def run(self, context: PipelineContext, input_bundle: dict[str, object]) -> PipelineResult:
        payload = await self.use_case.execute(
            trace_id=context.trace_id,
            request=context.request,
            production_bundle=input_bundle["production_bundle"],
            qa_bundle=input_bundle["qa_bundle"],
        )
        return PipelineResult.from_payload(payload)
