from app.Production.leader import ProductionLeader
from app.Production.skills import (
    AssetStorageSkill,
    ProductionRetryRecoverySkill,
    RenderExecuteSkill,
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
    """Canonical Production agent facade: production leader plus managed skill nodes."""

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
        ProductionRetryRecoverySkill,
    )
    department_domain = "production"
