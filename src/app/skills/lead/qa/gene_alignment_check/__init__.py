from __future__ import annotations

from typing import Any

from app.skills.base import BaseSkill


class GeneAlignmentCheckSkill(BaseSkill):
    skill_name = "lead.qa.gene_alignment_check"
    description = "Measures whether the produced script still matches the analyzed viral-content DNA."
    parameters_schema = {
        "type": "object",
        "properties": {
            "script": {"type": "object"},
            "analysis_bundle": {"type": "object"},
            "prompt_bundle": {"type": "object"},
        },
        "required": ["script", "analysis_bundle"],
    }
    tags = ["lead", "qa", "alignment"]
    retry_policy = {"max_retries": 1, "backoff": 0.0}
    dependencies = ["lead.analysis.hook_extraction", "lead.analysis.emotion_curve", "lead.research_development.prompt_package"]
    required_tokens = ["script", "analysis_bundle"]

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        script = input_data.get("script") or {}
        analysis_bundle = input_data.get("analysis_bundle") or {}
        reports = analysis_bundle.get("analysis_reports") or []
        prompt_bundle = input_data.get("prompt_bundle") or {}

        issues: list[str] = []
        score = 0.55
        scenes = list(script.get("scenes") or [])
        if script.get("hook"):
            score += 0.15
        else:
            issues.append("脚本缺少明确开场钩子。")

        if len(scenes) >= 3:
            score += 0.15
        else:
            issues.append("场景拆分偏少，节奏层次不足。")

        if reports:
            report = reports[0]
            reusable_elements = report.get("reusable_elements") or []
            script_text = " ".join(
                [
                    str(script.get("title") or ""),
                    str(script.get("hook") or ""),
                    str(script.get("cta") or ""),
                    " ".join(str(scene.get("text") or "") for scene in scenes),
                ]
            )
            matched = [item for item in reusable_elements if item and str(item) in script_text]
            if matched:
                score += 0.1
            else:
                issues.append("脚本对分析出的可复用爆款元素承接偏弱。")

        if prompt_bundle.get("title_candidates"):
            score += 0.05

        passed = score >= 0.7
        if passed and not issues:
            issues.append("脚本节奏、钩子与分析报告保持了基本一致。")

        return {
            "dimension": "gene_alignment",
            "applicable": True,
            "pass": passed,
            "score": round(min(max(score, 0.0), 1.0), 4),
            "issues": issues,
            "recommendation": "通过，可继续准备发布。" if passed else "建议回到研发/策划组微调标题、钩子与节奏。",
        }

    def validate_input(self, input_data: dict[str, Any]) -> bool:
        return isinstance(input_data, dict) and "script" in input_data and "analysis_bundle" in input_data

