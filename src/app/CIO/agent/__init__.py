from app.CIO.leader import InformationLeader
from app.CIO.skills import CIOLogSkill, KnowledgeBaseSkill, QueryLogSkill, RetrieveSkill, StoreSkill


class CIOAgent:
    """Canonical CIO agent facade: information leader plus managed skill nodes."""

    leader_class = InformationLeader
    managed_skill_classes = (StoreSkill, RetrieveSkill, CIOLogSkill, QueryLogSkill, KnowledgeBaseSkill)
    department_domain = "information_hub"

