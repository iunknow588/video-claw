from __future__ import annotations

from importlib import import_module

__all__ = [
    "ConfigReadSkill",
    "ConfigTransformSkill",
    "ConfigValidateSkill",
    "KnowledgeBaseSkill",
    "CIOLogSkill",
    "LogWorkflowSkill",
    "QueryLogSkill",
    "RetrieveSkill",
    "StoreSkill",
]

_EXPORTS = {
    "ConfigReadSkill": "app.CIO.skills.config_read",
    "ConfigTransformSkill": "app.CIO.skills.config_transform",
    "ConfigValidateSkill": "app.CIO.skills.config_validate",
    "KnowledgeBaseSkill": "app.CIO.skills.knowledge_base",
    "CIOLogSkill": "app.CIO.skills.log",
    "LogWorkflowSkill": "app.CIO.skills.workflow_log",
    "QueryLogSkill": "app.CIO.skills.query_log",
    "RetrieveSkill": "app.CIO.skills.retrieve",
    "StoreSkill": "app.CIO.skills.store",
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module = import_module(_EXPORTS[name])
    return getattr(module, name)
