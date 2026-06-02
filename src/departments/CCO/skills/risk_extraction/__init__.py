from __future__ import annotations


class RiskExtractionSkill:
    skill_name = "lead.analysis.risk_extraction"

    def run(self, input_bundle: dict) -> dict:
        return {
            **input_bundle,
            "risk_warnings": input_bundle.get("risk_warnings", []),
        }
