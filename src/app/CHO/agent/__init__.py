from app.CHO.leader import HumanOpsLeader
from app.CHO.services.service import CHOService
from app.CHO.skills import AgentCapabilitySkill, PublicAgentRegistrySkill, SharedAgentHealthSkill


class CHOAgent:
    """Canonical CHO agent facade: public-agent management leader plus shared agent governance skills."""

    leader_class = HumanOpsLeader
    service_class = CHOService
    managed_skill_classes = (PublicAgentRegistrySkill, AgentCapabilitySkill, SharedAgentHealthSkill)
    department_domain = "public_agent_management"
