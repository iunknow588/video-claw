from app.CQO.leader import QALeader
from app.CQO.skills import (
    ContentComplianceCheckSkill,
    DeliveryAssetCheckSkill,
    GeneAlignmentCheckSkill,
    QAReportSkill,
    RenderOutputCheckSkill,
    TechnicalSpecCheckSkill,
    VideoQualityCheckSkill,
)


class CQOAgent:
    """Canonical CQO agent facade: quality leader plus managed quality gate skills."""

    leader_class = QALeader
    managed_skill_classes = (
        VideoQualityCheckSkill,
        ContentComplianceCheckSkill,
        GeneAlignmentCheckSkill,
        TechnicalSpecCheckSkill,
        DeliveryAssetCheckSkill,
        RenderOutputCheckSkill,
        QAReportSkill,
    )
    department_domain = "quality_governance"

