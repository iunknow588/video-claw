from __future__ import annotations

from importlib import import_module
from typing import Any

from app.CEO.skills.base import BaseSkill


class ConfigTransformSkill(BaseSkill):
    skill_name = "lead.cio.config_transform"
    description = "Transforms validated config dictionaries into typed runtime models."
    parameters_schema = {
        "type": "object",
        "properties": {
            "data": {"type": "object"},
            "model_class": {"type": "string"},
        },
        "required": ["data", "model_class"],
    }
    tags = ["cio", "config", "transform"]

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        model_class = self._import_model(str(input_data["model_class"]))
        data = dict(input_data.get("data") or {})
        return {"instance": model_class.model_validate(data)}

    @staticmethod
    def _import_model(model_path: str):
        module_path, class_name = model_path.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, class_name)
