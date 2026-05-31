from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.skills.runtime import SkillDescriptor, build_descriptor


@dataclass(slots=True)
class SkillRegistry:
    handlers: dict[str, Any]
    descriptors: dict[str, SkillDescriptor]

    def __init__(self) -> None:
        self.handlers = {}
        self.descriptors = {}

    def register(self, name: str, handler: Any) -> None:
        self.handlers[name] = handler

    def register_instance(self, instance: Any, *, overrides: dict[str, Any] | None = None) -> SkillDescriptor:
        descriptor = build_descriptor(instance, overrides)
        self.handlers[descriptor.name] = instance
        self.descriptors[descriptor.name] = descriptor
        return descriptor

    def get(self, name: str) -> Any:
        if name not in self.handlers:
            raise KeyError(f"Skill not registered: {name}")
        return self.handlers[name]

    def get_descriptor(self, name: str) -> SkillDescriptor:
        if name not in self.descriptors:
            raise KeyError(f"Skill descriptor not registered: {name}")
        return self.descriptors[name]

    def list_descriptors(self) -> list[SkillDescriptor]:
        return [self.descriptors[name] for name in sorted(self.descriptors)]


registry = SkillRegistry()
