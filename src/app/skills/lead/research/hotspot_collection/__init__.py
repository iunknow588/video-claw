from __future__ import annotations


class HotspotCollectionSkill:
    skill_name = "lead.research.hotspot_collection"

    def run(self, input_bundle: dict) -> dict:
        return {"hotspots": input_bundle.get("hotspots", [])}

