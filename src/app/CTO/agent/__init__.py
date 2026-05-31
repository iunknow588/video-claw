from app.CTO.leader import PlanningLeader
from app.CTO.skills import PromptPackageSkill, PromptValidationSkill, PromptVersionSkill, TitleCandidateSkill


class CTOAgent:
    """Canonical CTO agent facade: planning leader plus managed technical planning skills."""

    leader_class = PlanningLeader
    managed_skill_classes = (PromptPackageSkill, TitleCandidateSkill, PromptValidationSkill, PromptVersionSkill)
    department_domain = "technology_planning"

