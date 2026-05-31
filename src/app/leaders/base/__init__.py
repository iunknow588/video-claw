from __future__ import annotations

from abc import ABC
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


class BaseLeader(ABC):
    """Unified lightweight leader contract for department-level governance."""

    name: str
    display_name: str
    description: str
    status: str
    version: int
    model: str | None
    system_prompt: str | None
    bound_tools: list[str]
    aliases: list[str]
    tags: list[str]
    token_limit: int
    resource_allocations: dict[str, Any]
    organization_profile: dict[str, Any]
    last_optimize_command: dict[str, Any] | None
    lifecycle_events: list[dict[str, Any]]
    version_history: list[dict[str, Any]]

    def get_status(self) -> dict[str, Any]:
        return asdict(self)  # type: ignore[arg-type]

    def accepts_alias(self, raw_name: str) -> bool:
        normalized = str(raw_name or "").strip().lower()
        if not normalized:
            return False
        keys = {self.name, self.name.removeprefix("lead."), self.display_name, *self.aliases}
        return normalized in {str(item).strip().lower() for item in keys}

    def remember_version(self) -> None:
        self.version_history.append(self.snapshot())

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "status": self.status,
            "version": self.version,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "bound_tools": list(self.bound_tools),
            "aliases": list(self.aliases),
            "tags": list(self.tags),
            "token_limit": self.token_limit,
            "resource_allocations": dict(self.resource_allocations),
            "organization_profile": deepcopy(self.organization_profile),
        }

    def restore(self, snapshot: dict[str, Any]) -> None:
        self.display_name = snapshot["display_name"]
        self.description = snapshot["description"]
        self.status = snapshot["status"]
        self.version = snapshot["version"]
        self.model = snapshot.get("model")
        self.system_prompt = snapshot.get("system_prompt")
        self.bound_tools = list(snapshot.get("bound_tools") or [])
        self.aliases = list(snapshot.get("aliases") or [])
        self.tags = list(snapshot.get("tags") or [])
        self.token_limit = int(snapshot.get("token_limit") or 10000)
        self.resource_allocations = dict(snapshot.get("resource_allocations") or {})
        self.organization_profile = dict(snapshot.get("organization_profile") or {})
        self.resource_allocations.setdefault("token_limit", self.token_limit)

    def apply_config(self, config: dict[str, Any]) -> None:
        if "display_name" in config:
            self.display_name = str(config["display_name"])
        if "description" in config:
            self.description = str(config["description"])
        if "status" in config:
            self.status = str(config["status"])
        if "model" in config:
            self.model = config["model"]
        if "system_prompt" in config:
            self.system_prompt = config["system_prompt"]
        if "bound_tools" in config:
            self.bound_tools = list(config["bound_tools"] or [])
        if "aliases" in config:
            self.aliases = list(config["aliases"] or [])
        if "tags" in config:
            self.tags = list(config["tags"] or [])
        if "token_limit" in config:
            self.token_limit = int(config["token_limit"])
        if "resource_allocations" in config:
            merged = dict(self.resource_allocations)
            merged.update(dict(config["resource_allocations"] or {}))
            self.resource_allocations = merged
        if "organization_profile" in config:
            merged_profile = dict(self.organization_profile)
            merged_profile.update(dict(config["organization_profile"] or {}))
            self.organization_profile = merged_profile
        self.resource_allocations.setdefault("token_limit", self.token_limit)

    def accept_command(
        self,
        *,
        command_type: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "command_type": command_type,
            "payload": deepcopy(payload or {}),
            "created_at": datetime.now(UTC),
        }
        self.lifecycle_events.append({"event_type": "command", "payload": event, "created_at": datetime.now(UTC)})
        if command_type == "optimize":
            self.last_optimize_command = deepcopy(payload or {})
        return event

    def build_report(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "status": self.status,
            "version": self.version,
            "bound_tools": list(self.bound_tools),
            "resource_allocations": dict(self.resource_allocations),
            "organization_profile": deepcopy(self.organization_profile),
            "last_optimize_command": deepcopy(self.last_optimize_command),
        }

    def build_periodic_report(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        report_context = deepcopy(context or {})
        return {
            **self.build_report(),
            "report_scope": "periodic",
            "submitted_at": datetime.now(UTC),
            "context": report_context,
        }

    def propose_change(self, proposal: dict[str, Any]) -> dict[str, Any]:
        accepted = {
            "leader_name": self.name,
            "proposal": deepcopy(proposal),
            "created_at": datetime.now(UTC),
        }
        self.lifecycle_events.append(
            {"event_type": "proposal_recorded", "payload": accepted, "created_at": datetime.now(UTC)}
        )
        return accepted


@dataclass(slots=True)
class ManagedLeader(BaseLeader):
    name: str
    display_name: str
    description: str
    status: str = "active"
    version: int = 1
    model: str | None = None
    system_prompt: str | None = None
    bound_tools: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    token_limit: int = 10000
    resource_allocations: dict[str, Any] = field(default_factory=dict)
    organization_profile: dict[str, Any] = field(default_factory=dict)
    last_optimize_command: dict[str, Any] | None = None
    lifecycle_events: list[dict[str, Any]] = field(default_factory=list)
    version_history: list[dict[str, Any]] = field(default_factory=list)
