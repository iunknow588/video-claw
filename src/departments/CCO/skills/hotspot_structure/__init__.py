from __future__ import annotations


class HotspotStructureSkill:
    skill_name = "lead.analysis.hotspot_structure"

    def run(self, input_bundle: dict) -> dict:
        return {
            **input_bundle,
            "content_structure": input_bundle.get("content_structure", input_bundle.get("structure", {})),
        }
