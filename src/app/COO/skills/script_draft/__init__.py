from __future__ import annotations


class ScriptDraftSkill:
    skill_name = "lead.production.script_draft"

    def run(self, input_bundle: dict) -> dict:
        return {"script_draft": input_bundle}

