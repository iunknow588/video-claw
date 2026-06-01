from app.CEO.services.control_plane.defaults import (
    CONTROL_PLANE_MISSION,
    CONTROL_PLANE_SCOPE,
    DEFAULT_LEADERS,
    DEFAULT_WORKFLOW,
)
from app.CEO.services.control_plane.runtime import CEOControlPlane


CEOControlPlane.mission = CONTROL_PLANE_MISSION
CEOControlPlane.managed_scope = CONTROL_PLANE_SCOPE

control_plane = CEOControlPlane()

__all__ = [
    "CEOControlPlane",
    "CONTROL_PLANE_MISSION",
    "CONTROL_PLANE_SCOPE",
    "DEFAULT_LEADERS",
    "DEFAULT_WORKFLOW",
    "control_plane",
]
