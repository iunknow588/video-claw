from __future__ import annotations

from departments.CIO.models.analysis import AnalysisReport


class ContentAnalysisUseCase:
    """CCO use case for content reverse engineering and persistence."""

    def __init__(self, assembly) -> None:
        self.assembly = assembly

    async def execute(self, *, trace_id: str, hotspots: list[dict]) -> dict:
        analysis_reports: list[AnalysisReport] = []
        analysis_bundles: list[dict] = []
        for hotspot_data in hotspots:
            hotspot = await self.assembly.load_hotspot(hotspot_data["uuid"])
            report = await self.assembly.analysis_service.analyze_content(hotspot)
            analysis_reports.append(report)
            base_bundle = self.assembly.serialize_analysis(report)
            structured_bundle = (
                await self.assembly.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.analysis",
                    skill=self.assembly.get_skill("lead.analysis.hotspot_structure"),
                    input_bundle=base_bundle,
                )
            ).output_json
            hook_bundle = (
                await self.assembly.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.analysis",
                    skill=self.assembly.get_skill("lead.analysis.hook_extraction"),
                    input_bundle=structured_bundle,
                )
            ).output_json
            emotion_bundle = (
                await self.assembly.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.analysis",
                    skill=self.assembly.get_skill("lead.analysis.emotion_curve"),
                    input_bundle=hook_bundle,
                )
            ).output_json
            risk_bundle = (
                await self.assembly.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.analysis",
                    skill=self.assembly.get_skill("lead.analysis.risk_extraction"),
                    input_bundle=emotion_bundle,
                )
            ).output_json
            reusable_bundle = (
                await self.assembly.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.analysis",
                    skill=self.assembly.get_skill("lead.analysis.reusable_element"),
                    input_bundle=risk_bundle,
                )
            ).output_json
            persisted_bundle = (
                await self.assembly.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.analysis",
                    skill=self.assembly.get_skill("lead.analysis.analysis_persist"),
                    input_bundle={"trace_id": trace_id, **reusable_bundle, "analysis_id": report.uuid},
                )
            ).output_json
            analysis_bundles.append(persisted_bundle["analysis_bundle"])

        return {
            "analysis_reports": analysis_reports,
            "bundle": {
                "analysis_reports": analysis_bundles,
                "analysis_ids": [report.uuid for report in analysis_reports],
            },
            "notes": [f"analysis_count={len(analysis_reports)}"],
        }
