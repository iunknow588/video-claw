from __future__ import annotations


class AnalysisPersistSkill:
    skill_name = "lead.analysis.analysis_persist"

    def run(self, input_bundle: dict) -> dict:
        return {"analysis_bundle": input_bundle}

