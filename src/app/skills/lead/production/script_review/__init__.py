from __future__ import annotations


class ScriptReviewSkill:
    skill_name = "lead.production.script_review"

    def run(self, input_bundle: dict) -> dict:
        return {"approved": True, "script_bundle": input_bundle}

