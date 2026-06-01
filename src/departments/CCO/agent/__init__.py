from departments.CCO.leader import AnalysisLeader
from departments.CCO.skills import (
    AnalysisPersistSkill,
    EmotionCurveSkill,
    HookExtractionSkill,
    HotspotStructureSkill,
    ReusableElementSkill,
    RiskExtractionSkill,
)


class AnalysisAgent:
    """Canonical CCO agent facade: analysis leader plus content reverse-engineering skills."""

    leader_class = AnalysisLeader
    managed_skill_classes = (
        HotspotStructureSkill,
        HookExtractionSkill,
        EmotionCurveSkill,
        RiskExtractionSkill,
        ReusableElementSkill,
        AnalysisPersistSkill,
    )
    department_domain = "analysis"


__all__ = ["AnalysisAgent"]
