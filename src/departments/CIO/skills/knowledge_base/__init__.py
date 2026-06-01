from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.services.knowledge import CIOInformationService
from departments.CEO.skills.base import BaseSkill


class KnowledgeBaseSkill(BaseSkill):
    skill_name = "lead.cio.knowledge_base"
    description = "Maintains lightweight knowledge assets such as templates, platform guides, and viral-case notes."
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string"},
            "category": {"type": "string"},
            "asset": {"type": "object"},
        },
        "required": ["action"],
    }
    tags = ["lead", "cio", "knowledge", "repository"]
    dependencies = ["lead.cio.store", "lead.cio.retrieve"]
    required_tokens = ["category", "asset"]

    def __init__(self, session: AsyncSession | None = None, config: dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        self.service = CIOInformationService(session)

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("lead.cio.knowledge_base must be invoked through async_execute")

    async def async_execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        action = str(input_data.get("action") or "").strip().lower()
        category = str(input_data.get("category") or "").strip() or None

        if action == "summary":
            assets = await self.service.list_knowledge_assets(category)
            return {
                "knowledge_summary": {
                    "category": category,
                    "asset_count": sum(len(bucket) for bucket in assets.values()),
                    "categories": {name: len(bucket) for name, bucket in assets.items()},
                }
            }
        if action == "list":
            return {"knowledge_assets": await self.service.list_knowledge_assets(category)}
        if action == "upsert":
            asset = await self.service.upsert_knowledge_asset(
                category=category or "general",
                asset=dict(input_data.get("asset") or {}),
            )
            return {"knowledge_asset": asset}
        raise ValueError(f"Unsupported action for {self.skill_name}: {action}")
