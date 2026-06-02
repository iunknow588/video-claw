from __future__ import annotations


class HookExtractionSkill:
    skill_name = "lead.analysis.hook_extraction"

    def run(self, input_bundle: dict) -> dict:
        return {
            **input_bundle,
            "hook_design": input_bundle.get("hook_design", input_bundle.get("hook", "")),
        }
