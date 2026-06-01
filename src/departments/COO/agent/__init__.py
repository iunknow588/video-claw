from departments.COO.leader import ProductionLeader
from departments.COO.skills import (
    AssetStorageSkill,
    RenderExecuteSkill,
    RetryRecoverySkill,
    ScriptDraftSkill,
    ScriptReviewSkill,
    SubtitleComposeSkill,
    VideoComposePlanSkill,
    VideoProcessSkill,
    VideoReviewSkill,
    VideoTaskSkill,
    VoiceoverGenerateSkill,
)


class ProductionAgent:
    """Canonical COO agent facade: production execution leader plus managed execution skills."""

    leader_class = ProductionLeader
    managed_skill_classes = (
        ScriptDraftSkill,
        ScriptReviewSkill,
        SubtitleComposeSkill,
        VoiceoverGenerateSkill,
        VideoTaskSkill,
        VideoProcessSkill,
        VideoReviewSkill,
        VideoComposePlanSkill,
        RenderExecuteSkill,
        AssetStorageSkill,
        RetryRecoverySkill,
    )
    department_domain = "production"


__all__ = ["ProductionAgent"]
