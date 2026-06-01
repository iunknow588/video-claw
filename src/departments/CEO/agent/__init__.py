from departments.CEO.control import CEOControlService, control_plane
from departments.CEO.skills.workflow import CEOWorkflowSkill


class CEOAgent:
    """Canonical CEO agent facade: governance control plane plus orchestration skill entrypoints."""

    control_service = CEOControlService
    workflow_skill = CEOWorkflowSkill
    managed_scope = "company_governance"
    control_plane = control_plane
