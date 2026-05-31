from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any


class BaseSkill(ABC):
    """Framework-level skill contract with lightweight defaults."""

    name: str = ""
    skill_name: str = ""
    description: str = ""
    parameters_schema: dict[str, Any] = {}
    tags: list[str] = []
    default_config: dict[str, Any] = {}
    retry_policy: dict[str, Any] = {"max_retries": 1, "backoff": 0.0}
    dependencies: list[str] = []
    required_tokens: list[str] = []

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = {**self.default_config, **(config or {})}
        self.progress = 0.0
        self.status_message = ""

    @classmethod
    def canonical_name(cls) -> str:
        return cls.skill_name or cls.name or f"{cls.__module__}.{cls.__name__}"

    @abstractmethod
    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    async def async_execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return self.execute(input_data)

    def execute_stream(self, input_data: dict[str, Any]) -> Iterator[dict[str, Any]]:
        yield {"type": "progress", "progress": 0.0, "message": "started"}
        result = self.execute(input_data)
        yield {"type": "result", "progress": 1.0, "message": "completed", "data": result}

    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return self.execute(input_data)

    def setup(self) -> None:
        return None

    def teardown(self) -> None:
        return None

    def validate_input(self, input_data: dict[str, Any]) -> bool:
        return isinstance(input_data, dict)

    def on_error(self, error: Exception, input_data: dict[str, Any]) -> Any:
        raise error
