from __future__ import annotations


class PromptVersionSkill:
    skill_name = "lead.research_development.prompt_version"

    def run(self, input_bundle: dict) -> dict:
        return {"version": 1, "prompt_bundle": input_bundle}

