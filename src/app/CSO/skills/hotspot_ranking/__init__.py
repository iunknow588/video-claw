from __future__ import annotations


class HotspotRankingSkill:
    skill_name = "lead.research.hotspot_ranking"

    def run(self, input_bundle: dict) -> dict:
        hotspots = input_bundle.get("hotspots", [])
        ranked = sorted(
            hotspots,
            key=lambda item: item.get("heat_score", 0) if isinstance(item, dict) else 0,
            reverse=True,
        )
        return {"hotspots": ranked}
