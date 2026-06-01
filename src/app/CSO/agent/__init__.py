from app.CSO.leader import ResearchLeader
from app.CSO.skills import (
    DomainQueryExpansionSkill,
    HotspotCollectionSkill,
    HotspotDedupSkill,
    HotspotRankingSkill,
    HotspotSnapshotSkill,
    MaterialSearchSkill,
)


class ResearchAgent:
    """Canonical CSO agent facade: research leader plus hotspot and material planning skills."""

    leader_class = ResearchLeader
    managed_skill_classes = (
        DomainQueryExpansionSkill,
        HotspotCollectionSkill,
        HotspotDedupSkill,
        HotspotRankingSkill,
        HotspotSnapshotSkill,
        MaterialSearchSkill,
    )
    department_domain = "research"


__all__ = ["ResearchAgent"]
