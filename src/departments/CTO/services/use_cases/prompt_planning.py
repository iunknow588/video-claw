from __future__ import annotations

from departments.CIO.models.analysis import AnalysisReport
from departments.CIO.schemas.video import DomainWorkflowRequest


class PromptPlanningUseCase:
    """CTO use case for prompt packaging, title generation, validation, and versioning."""

    def __init__(self, assembly) -> None:
        self.assembly = assembly

    async def execute(
        self,
        *,
        trace_id: str,
        request: DomainWorkflowRequest,
        domain: str,
        hotspots: list[dict],
        analyses: list[AnalysisReport],
    ) -> dict:
        prompt_package = self.assembly.trend_service.build_prompt_package(
            domain=domain,
            hotspots=[self.assembly.load_hotspot_sync(item) for item in hotspots],
            analyses=analyses,
            platform=request.platform,
            duration=request.duration,
            style=request.style,
            content_type=request.content_type,
            audience=request.audience,
            publish_goal=request.publish_goal,
        )
        prompt_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research_development",
                skill=self.assembly.get_skill("lead.research_development.prompt_package"),
                input_bundle={"trace_id": trace_id, **prompt_package},
            )
        ).output_json["prompt_bundle"]
        title_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research_development",
                skill=self.assembly.get_skill("lead.research_development.title_candidate"),
                input_bundle={"trace_id": trace_id, **prompt_bundle},
            )
        ).output_json
        validation_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research_development",
                skill=self.assembly.get_skill("lead.research_development.prompt_validation"),
                input_bundle={"trace_id": trace_id, **prompt_bundle, **title_bundle},
            )
        ).output_json
        if not validation_bundle.get("passed", validation_bundle.get("valid", False)):
            issue_summary = "; ".join(str(item) for item in validation_bundle.get("issues", [])[:3]) or "unknown issue"
            raise ValueError(f"Prompt validation failed: {issue_summary}")
        version_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research_development",
                skill=self.assembly.get_skill("lead.research_development.prompt_version"),
                input_bundle={"trace_id": trace_id, **validation_bundle},
            )
        ).output_json
        enriched_prompt_package = {
            **prompt_package,
            "title_candidates": title_bundle.get("title_candidates", prompt_package.get("title_candidates", [])),
            "quality_score": version_bundle.get("quality_score"),
            "version": version_bundle.get("version", 1),
            "version_label": version_bundle.get("version_label"),
            "fingerprint": version_bundle.get("fingerprint"),
            "validation_issues": validation_bundle.get("issues", []),
            "validation_warnings": validation_bundle.get("warnings", []),
        }
        enriched_prompt_bundle = {
            **prompt_bundle,
            "title_candidates": title_bundle.get("title_candidates", prompt_bundle.get("title_candidates", [])),
            "quality_score": validation_bundle.get("quality_score"),
            "validation": {
                "passed": validation_bundle.get("passed", validation_bundle.get("valid", True)),
                "issues": validation_bundle.get("issues", []),
                "warnings": validation_bundle.get("warnings", []),
            },
            "version": version_bundle.get("version", 1),
            "version_label": version_bundle.get("version_label"),
            "fingerprint": version_bundle.get("fingerprint"),
        }
        return {
            "prompt_package": enriched_prompt_package,
            "prompt_bundle": enriched_prompt_bundle,
            "title_candidates": title_bundle.get("title_candidates", []),
            "validation": validation_bundle,
            "version": version_bundle.get("version", 1),
            "version_bundle": version_bundle,
            "notes": [
                f"prompt_version={version_bundle.get('version', 1)}",
                f"prompt_quality={validation_bundle.get('quality_score', 0.0)}",
            ],
        }
