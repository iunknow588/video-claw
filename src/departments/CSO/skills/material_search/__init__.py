from __future__ import annotations

from typing import Any

from departments.CSO.services.material_reference import MaterialReferenceService
from departments.CEO.skills.base import BaseSkill


class MaterialSearchSkill(BaseSkill):
    skill_name = "lead.research.material_search"
    description = "Plans reusable material-search candidates, cache keys, and scene mappings for downstream production."
    parameters_schema = {
        "type": "object",
        "properties": {
            "search_terms": {"type": "array", "items": {"type": "string"}},
            "scenes": {"type": "array", "items": {"type": "object"}},
            "platform": {"type": "string"},
            "target_duration": {"type": "integer"},
            "aspect_ratio": {"type": "string"},
            "limit_per_term": {"type": "integer"},
            "material_pool": {"type": "array", "items": {"type": "object"}},
        },
        "required": [],
    }
    tags = ["lead", "CSO", "material", "planning"]
    dependencies = []

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        self.service = MaterialReferenceService()

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return self.service.plan(
            search_terms=list(input_data.get("search_terms") or []),
            scenes=list(input_data.get("scenes") or []),
            platform=input_data.get("platform"),
            target_duration=input_data.get("target_duration"),
            aspect_ratio=str(input_data.get("aspect_ratio") or "9:16"),
            limit_per_term=int(input_data.get("limit_per_term") or 2),
            material_pool=list(input_data.get("material_pool") or []),
            provider=str(input_data.get("provider") or "reference_stub"),
        )
