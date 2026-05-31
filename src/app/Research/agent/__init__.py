from app.Research.leader import ResearchLeader
from app.Research.skills import (
    DomainQueryExpansionSkill,
    HotspotCollectionSkill,
    HotspotDedupSkill,
    HotspotRankingSkill,
    HotspotSnapshotSkill,
    MaterialSearchSkill,
)


class ResearchAgent:
    """Canonical Research agent facade: research leader plus managed skill nodes."""

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
