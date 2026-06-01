from __future__ import annotations

from dataclasses import dataclass
import importlib
import inspect
from typing import Any

from app.CEO.skills.runtime import SkillDescriptor, build_descriptor


DEPARTMENT_SKILL_MODULES = (
    "app.CEO.skills",
    "app.CFO.skills",
    "app.CIO.skills",
    "app.CHO.skills",
    "app.CMO.skills",
    "app.CSO.skills",
    "app.CCO.skills",
    "app.CTO.skills",
    "app.COO.skills",
    "app.CQO.skills",
    "app.CAO.skills",
)


@dataclass(slots=True)
class SkillFactoryContext:
    session: Any | None = None


@dataclass(slots=True)
class SkillRegistration:
    skill_class: type[Any]

    def instantiate(self, context: SkillFactoryContext) -> Any:
        return instantiate_skill(self.skill_class, context)


class SkillRegistryScope:
    def __init__(self, registry: SkillRegistry, *, session: Any | None = None):
        self._registry = registry
        self._context = SkillFactoryContext(session=session)
        self._instances: dict[str, Any] = {}

    def get(self, name: str) -> Any:
        if name not in self._instances:
            self._instances[name] = self._registry.create_instance(name, context=self._context)
        return self._instances[name]

    def get_descriptor(self, name: str) -> SkillDescriptor:
        return self._registry.get_descriptor(name)

    def list_descriptors(self) -> list[SkillDescriptor]:
        return self._registry.list_descriptors()


class SkillRegistry:
    registrations: dict[str, SkillRegistration]
    descriptors: dict[str, SkillDescriptor]

    def __init__(self) -> None:
        self.registrations = {}
        self.descriptors = {}
        self._bootstrapped = False

    def register_class(self, skill_class: type[Any]) -> SkillDescriptor:
        descriptor = build_descriptor(instantiate_skill(skill_class, SkillFactoryContext()))
        existing = self.registrations.get(descriptor.name)
        if existing and existing.skill_class is skill_class:
            return self.descriptors[descriptor.name]
        self.registrations[descriptor.name] = SkillRegistration(skill_class=skill_class)
        self.descriptors[descriptor.name] = descriptor
        return descriptor

    def create_instance(self, name: str, *, context: SkillFactoryContext | None = None) -> Any:
        if name not in self.registrations:
            raise KeyError(f"Skill not registered: {name}")
        return self.registrations[name].instantiate(context or SkillFactoryContext())

    def bind(self, *, session: Any | None = None) -> SkillRegistryScope:
        return SkillRegistryScope(self, session=session)

    def get_descriptor(self, name: str) -> SkillDescriptor:
        if name not in self.descriptors:
            raise KeyError(f"Skill descriptor not registered: {name}")
        return self.descriptors[name]

    def list_descriptors(self) -> list[SkillDescriptor]:
        return [self.descriptors[name] for name in sorted(self.descriptors)]

    def ensure_builtin_skills_registered(self) -> None:
        if self._bootstrapped:
            return
        for module_name in DEPARTMENT_SKILL_MODULES:
            module = importlib.import_module(module_name)
            export_names = getattr(module, "__all__", ())
            for export_name in export_names:
                exported = getattr(module, export_name, None)
                if not inspect.isclass(exported):
                    continue
                skill_name = getattr(exported, "skill_name", None)
                if not skill_name:
                    continue
                self.register_class(exported)
        self._bootstrapped = True


def instantiate_skill(skill_class: type[Any], context: SkillFactoryContext) -> Any:
    signature = inspect.signature(skill_class)
    kwargs: dict[str, Any] = {}
    if "session" in signature.parameters:
        kwargs["session"] = context.session
    return skill_class(**kwargs)


registry = SkillRegistry()


def ensure_builtin_skills_registered() -> None:
    registry.ensure_builtin_skills_registered()
