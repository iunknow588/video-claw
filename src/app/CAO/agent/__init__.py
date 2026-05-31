from app.CAO.leader import CAOLeader
from app.CAO.skills import (
    PlatformAdapterSkill,
    PublishCallbackSkill,
    PublishExecuteSkill,
    PublishHistorySkill,
    PublishPlanSkill,
    PublishRetryRecoverySkill,
)


class CAOAgent:
    """Canonical CAO agent facade: external API gateway leader plus managed publish and callback skills."""

    leader_class = CAOLeader
    managed_skill_classes = (
        PublishPlanSkill,
        PlatformAdapterSkill,
        PublishExecuteSkill,
        PublishCallbackSkill,
        PublishHistorySkill,
        PublishRetryRecoverySkill,
    )
    department_domain = "external_api_gateway"
