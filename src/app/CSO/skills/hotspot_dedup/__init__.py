from __future__ import annotations


class HotspotDedupSkill:
    skill_name = "lead.research.hotspot_dedup"

    def run(self, input_bundle: dict) -> dict:
        hotspots = input_bundle.get("hotspots", [])
        seen = set()
        unique = []
        for item in hotspots:
            key = item.get("content_id") if isinstance(item, dict) else str(item)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return {"hotspots": unique}

