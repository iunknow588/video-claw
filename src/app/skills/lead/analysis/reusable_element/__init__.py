from __future__ import annotations


class ReusableElementSkill:
    skill_name = "lead.analysis.reusable_element"

    def run(self, input_bundle: dict) -> dict:
        return {"reusable_elements": input_bundle.get("reusable_elements", [])}

