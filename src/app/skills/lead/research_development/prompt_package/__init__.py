from __future__ import annotations


class PromptPackageSkill:
    skill_name = "lead.research_development.prompt_package"

    def run(self, input_bundle: dict) -> dict:
        return {"prompt_bundle": input_bundle}

