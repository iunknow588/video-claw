from __future__ import annotations

from fastapi.encoders import jsonable_encoder

from departments.CIO.schemas.video import DomainWorkflowRequest


class QualityGateUseCase:
    """CQO use case for multi-dimensional quality checks and routing decisions."""

    def __init__(self, assembly) -> None:
        self.assembly = assembly

    async def execute(
        self,
        *,
        trace_id: str,
        request: DomainWorkflowRequest,
        prompt_bundle: dict,
        analysis_bundle: dict,
        production_bundle: dict,
    ) -> dict:
        script = production_bundle["script"]
        video_task = production_bundle.get("video_task")
        serialized_script = self.assembly.serialize_script(script)
        serialized_video_task = self.assembly.serialize_video_task(video_task) if video_task else None
        checks = []
        for skill_name, payload in [
            (
                "lead.qa.video_quality_check",
                {"trace_id": trace_id, "platform": request.platform, "video_task": serialized_video_task},
            ),
            (
                "lead.qa.content_compliance_check",
                {
                    "trace_id": trace_id,
                    "platform": request.platform,
                    "script": serialized_script,
                    "video_task": serialized_video_task,
                },
            ),
            (
                "lead.qa.gene_alignment_check",
                {
                    "trace_id": trace_id,
                    "script": serialized_script,
                    "analysis_bundle": analysis_bundle,
                    "prompt_bundle": prompt_bundle,
                },
            ),
            (
                "lead.qa.technical_spec_check",
                {
                    "trace_id": trace_id,
                    "platform": request.platform,
                    "script": serialized_script,
                    "video_task": serialized_video_task,
                },
            ),
            (
                "lead.qa.delivery_asset_check",
                {
                    "trace_id": trace_id,
                    "script": serialized_script,
                    "material_bundle": production_bundle.get("material_bundle") or {},
                    "subtitle_bundle": production_bundle.get("subtitle_bundle") or {},
                    "voiceover_bundle": production_bundle.get("voiceover_bundle") or {},
                    "composition_bundle": production_bundle.get("composition_bundle") or {},
                },
            ),
            (
                "lead.qa.render_output_check",
                {
                    "trace_id": trace_id,
                    "platform": request.platform,
                    "render_bundle": production_bundle.get("render_bundle") or {},
                },
            ),
        ]:
            checks.append(
                (
                    await self.assembly.recorder.call_skill(
                        trace_id=trace_id,
                        parent_id="lead.qa",
                        skill=self.assembly.get_skill(skill_name),
                        input_bundle=payload,
                    )
                ).output_json
            )

        qa_report = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.qa",
                skill=self.assembly.get_skill("lead.qa.qa_report"),
                input_bundle={"trace_id": trace_id, "checks": checks, "video_task": serialized_video_task},
            )
        ).output_json["qa_report"]
        if video_task:
            video_task.quality_score = qa_report["overall_score"]
            video_task.quality_report = jsonable_encoder({"checks": checks, "qa_report": qa_report, "trace_id": trace_id})
            await self.assembly.session.flush()

        return {
            "qa_report": qa_report,
            "bundle": {
                "checks": checks,
                "qa_report": qa_report,
                "video_task": self.assembly.serialize_video_task(video_task) if video_task else None,
            },
            "notes": [f"qa_status={qa_report['qa_status']}"],
        }
