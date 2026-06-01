from __future__ import annotations

from importlib import import_module

__all__ = ["CEOWorkflowSkill"]

_EXPORTS = {
    "CEOWorkflowSkill": "departments.CEO.skills.workflow",
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module = import_module(_EXPORTS[name])
    return getattr(module, name)
