from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.CEO.core.config import settings
from app.CEO.config.schema import ControlPlaneLeadersConfig, WorkflowGovernanceConfig
from app.CEO.leaders.organization import apply_org_naming_defaults


def get_control_plane_mission() -> str:
    leaders: ControlPlaneLeadersConfig = settings.leaders
    return leaders.mission


def get_control_plane_scope() -> str:
    leaders: ControlPlaneLeadersConfig = settings.leaders
    return leaders.scope


def get_default_leaders() -> dict[str, dict[str, Any]]:
    leaders: ControlPlaneLeadersConfig = settings.leaders
    return {
        name: apply_org_naming_defaults(name, config.model_dump(mode="python"))
        for name, config in leaders.leaders.items()
    }


def get_default_workflow() -> dict[str, Any]:
    workflow: WorkflowGovernanceConfig = settings.workflow
    return deepcopy(workflow.model_dump(mode="python", by_alias=True))


CONTROL_PLANE_MISSION = get_control_plane_mission()
CONTROL_PLANE_SCOPE = get_control_plane_scope()
DEFAULT_LEADERS: dict[str, dict[str, Any]] = get_default_leaders()

DEFAULT_WORKFLOW: dict[str, Any] = get_default_workflow()
