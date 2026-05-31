from app.Analysis.leader import AnalysisLeader
from app.Analysis.skills import (
    AnalysisPersistSkill,
    EmotionCurveSkill,
    HookExtractionSkill,
    HotspotStructureSkill,
    ReusableElementSkill,
    RiskExtractionSkill,
)


class AnalysisAgent:
    """Canonical Analysis agent facade: analysis leader plus managed skill nodes."""

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
