from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

from departments.CEO.skills.base import BaseSkill


class ConfigReadSkill(BaseSkill):
    skill_name = "lead.cio.config_read"
    description = "Reads structured configuration files and resolves environment placeholders."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "format": {"type": "string"},
        },
        "required": ["path"],
    }
    tags = ["cio", "config", "read"]

    _placeholder_pattern = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        path = Path(str(input_data["path"]))
        format_type = str(input_data.get("format") or path.suffix.lstrip(".") or "yaml").lower()
        if format_type in {"yaml", "yml"}:
            with path.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
        elif format_type == "json":
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        else:
            raise ValueError(f"Unsupported config format: {format_type}")
        return {"data": self._resolve_placeholders(data), "path": str(path)}

    def _resolve_placeholders(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._resolve_placeholders(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve_placeholders(item) for item in value]
        if isinstance(value, str):
            return self._placeholder_pattern.sub(self._replace_placeholder, value)
        return value

    @staticmethod
    def _replace_placeholder(match: re.Match[str]) -> str:
        env_name = match.group(1)
        default = match.group(2) or ""
        return os.environ.get(env_name, default)
