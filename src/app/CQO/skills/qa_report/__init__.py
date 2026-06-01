from __future__ import annotations

from typing import Any

from app.CEO.skills.base import BaseSkill


class QAReportSkill(BaseSkill):
    skill_name = "lead.qa.qa_report"
    description = "Aggregates QA dimensions into a final quality gate decision and rework recommendation."
    parameters_schema = {
        "type": "object",
        "properties": {
            "checks": {"type": "array"},
            "video_task": {"type": ["object", "null"]},
        },
        "required": ["checks"],
    }
    tags = ["lead", "qa", "report"]
    retry_policy = {"max_retries": 1, "backoff": 0.0}
    dependencies = [
        "lead.qa.video_quality_check",
        "lead.qa.content_compliance_check",
        "lead.qa.gene_alignment_check",
        "lead.qa.technical_spec_check",
        "lead.qa.delivery_asset_check",
        "lead.qa.render_output_check",
    ]
    required_tokens = ["checks"]

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        checks = list(input_data.get("checks") or [])
        applicable = [item for item in checks if item.get("applicable", True)]
        failed = [item for item in applicable if not item.get("pass", False)]
        overall_score = (
            round(sum(float(item.get("score", 0.0) or 0.0) for item in applicable) / max(len(applicable), 1), 4)
            if applicable
            else 1.0
        )
        video_task = input_data.get("video_task") or {}

        qa_passed = not failed and overall_score >= 0.75
        flat_issues = [
            {"dimension": item.get("dimension"), "issues": list(item.get("issues") or [])}
            for item in checks
        ]
        recommendation = (
            "质检通过，允许进入发布组。"
            if qa_passed
            else "质检未通过，建议退回上游部门处理后再复检。"
        )

        return {
            "qa_report": {
                "pass": qa_passed,
                "qa_status": "passed" if qa_passed else "failed",
                "overall_score": overall_score,
                "failed_dimensions": [item.get("dimension") for item in failed],
                "issues": flat_issues,
                "recommendation": recommendation,
                "retry_recommended": bool(failed) and bool(video_task),
            }
        }

    def validate_input(self, input_data: dict[str, Any]) -> bool:
        return isinstance(input_data, dict) and "checks" in input_data
