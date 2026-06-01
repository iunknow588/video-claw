from app.CTO.leader import PlanningLeader
from app.CTO.skills import PromptPackageSkill, PromptValidationSkill, PromptVersionSkill, TitleCandidateSkill


class CTOAgent:
    """Canonical CTO agent facade: planning leader plus prompt and validation skills."""

    leader_class = PlanningLeader
    managed_skill_classes = (
        PromptPackageSkill,
        TitleCandidateSkill,
        PromptValidationSkill,
        PromptVersionSkill,
    )
    department_domain = "planning"


__all__ = ["CTOAgent"]
