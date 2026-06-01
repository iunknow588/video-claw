from departments.CMO.leader import CMOLeader
from departments.CMO.services.chat import CMOService
from departments.CMO.skills import ChatUISkill, ProgressUISkill, ReportUISkill


class CMOAgent:
    """Canonical CMO agent facade: promotion leader, service agent, and managed UI skills."""

    leader_class = CMOLeader
    service_class = CMOService
    managed_skill_classes = (ChatUISkill, ProgressUISkill, ReportUISkill)
    department_domain = "promotion_interface"
