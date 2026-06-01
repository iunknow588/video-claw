from __future__ import annotations

from app.CIO.schemas.video import DomainWorkflowRequest, HotspotFetchRequest


class ResearchUseCase:
    """CSO use case for query expansion, hotspot collection, ranking, and snapshotting."""

    def __init__(self, assembly) -> None:
        self.assembly = assembly

    async def execute(self, *, trace_id: str, request: DomainWorkflowRequest) -> dict:
        expanded_queries = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research",
                skill=self.assembly.get_skill("lead.research.domain_query_expansion"),
                input_bundle={
                    "trace_id": trace_id,
                    "domain": request.domain,
                    "audience": request.audience,
                    "publish_goal": request.publish_goal,
                },
            )
        ).output_json["expanded_queries"]

        per_query = max(1, request.hotspot_count // max(len(expanded_queries), 1))
        collected: list[dict] = []
        for query in expanded_queries:
            items = await self.assembly.hotspot_service.fetch_hotspots(
                HotspotFetchRequest(platform=request.platform, keyword=query, count=per_query + 1)
            )
            collected.extend(self.assembly.serialize_hotspot(item) for item in items)

        collected_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research",
                skill=self.assembly.get_skill("lead.research.hotspot_collection"),
                input_bundle={"trace_id": trace_id, "hotspots": collected},
            )
        ).output_json
        dedup_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research",
                skill=self.assembly.get_skill("lead.research.hotspot_dedup"),
                input_bundle={"trace_id": trace_id, "hotspots": collected_bundle["hotspots"]},
            )
        ).output_json
        ranked_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research",
                skill=self.assembly.get_skill("lead.research.hotspot_ranking"),
                input_bundle={"trace_id": trace_id, "hotspots": dedup_bundle["hotspots"]},
            )
        ).output_json
        selected_hotspots = list(ranked_bundle["hotspots"][: request.top_n])
        snapshot_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research",
                skill=self.assembly.get_skill("lead.research.hotspot_snapshot"),
                input_bundle={
                    "trace_id": trace_id,
                    "domain": request.domain,
                    "expanded_queries": expanded_queries,
                    "selected_hotspots": selected_hotspots,
                    "hotspot_pool": ranked_bundle["hotspots"],
                },
            )
        ).output_json
        return {
            "expanded_queries": expanded_queries,
            "selected_hotspots": selected_hotspots,
            "bundle": {
                "expanded_queries": expanded_queries,
                "hotspot_pool": ranked_bundle["hotspots"],
                "selected_hotspots": selected_hotspots,
                "snapshot": snapshot_bundle["hotspot_bundle"],
            },
            "notes": [f"research_selected={len(selected_hotspots)}"],
        }
