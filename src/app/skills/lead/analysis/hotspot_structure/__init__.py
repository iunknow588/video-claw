from __future__ import annotations


class HotspotStructureSkill:
    skill_name = "lead.analysis.hotspot_structure"

    def run(self, input_bundle: dict) -> dict:
        return {"structure": input_bundle.get("structure", {})}

