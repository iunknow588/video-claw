from __future__ import annotations


class HotspotSnapshotSkill:
    skill_name = "lead.research.hotspot_snapshot"

    def run(self, input_bundle: dict) -> dict:
        return {"hotspot_bundle": input_bundle}

