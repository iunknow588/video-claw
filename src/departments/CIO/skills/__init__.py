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
    "ConfigReadSkill": "departments.CIO.skills.config_read",
    "ConfigTransformSkill": "departments.CIO.skills.config_transform",
    "ConfigValidateSkill": "departments.CIO.skills.config_validate",
    "KnowledgeBaseSkill": "departments.CIO.skills.knowledge_base",
    "CIOLogSkill": "departments.CIO.skills.log",
    "LogWorkflowSkill": "departments.CIO.skills.workflow_log",
    "QueryLogSkill": "departments.CIO.skills.query_log",
    "RetrieveSkill": "departments.CIO.skills.retrieve",
    "StoreSkill": "departments.CIO.skills.store",
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module = import_module(_EXPORTS[name])
    return getattr(module, name)
