from __future__ import annotations

from importlib import import_module
from typing import Any

from pydantic import ValidationError

from app.CEO.skills.base import BaseSkill


class ConfigValidateSkill(BaseSkill):
    skill_name = "lead.cio.config_validate"
    description = "Validates raw configuration payloads against typed schemas."
    parameters_schema = {
        "type": "object",
        "properties": {
            "data": {"type": "object"},
            "model_class": {"type": "string"},
        },
        "required": ["data", "model_class"],
    }
    tags = ["cio", "config", "validate"]

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        model_class = self._import_model(str(input_data["model_class"]))
        data = dict(input_data.get("data") or {})
        try:
            instance = model_class.model_validate(data)
        except ValidationError as exc:
            return {
                "valid": False,
                "errors": [
                    {
                        "loc": ".".join(str(part) for part in error["loc"]),
                        "message": error["msg"],
                        "type": error["type"],
                    }
                    for error in exc.errors()
                ],
            }
        return {
            "valid": True,
            "errors": [],
            "normalized_data": instance.model_dump(mode="python", by_alias=True),
        }

    @staticmethod
    def _import_model(model_path: str):
        module_path, class_name = model_path.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, class_name)
