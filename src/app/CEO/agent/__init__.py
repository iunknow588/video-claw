from app.CEO.control import CEOChatService, CEOControlService, control_plane
from app.CEO.skills import CEOWorkflowSkill


class CEOAgent:
    """Canonical CEO agent facade: control plane + interaction + owned skill entrypoints."""

    control_service = CEOControlService
    chat_service = CEOChatService
    workflow_skill = CEOWorkflowSkill
    managed_scope = "company_governance"
    control_plane = control_plane

