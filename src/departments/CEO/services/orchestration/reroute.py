from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

PLANNING_REWORK_DIMENSIONS = {"content_compliance", "gene_alignment"}
PRODUCTION_REWORK_DIMENSIONS = {"video_quality", "technical_spec", "delivery_asset", "render_output"}


@dataclass(slots=True)
class QARerouteDecision:
    strategy: str
    route_key: str
    target: str


class QARerouteStrategy(ABC):
    name = ""

    @abstractmethod
    def determine_route_key(self, qa_report: dict[str, Any]) -> str:
        ...


class BalancedQARerouteStrategy(QARerouteStrategy):
    name = "balanced"

    def determine_route_key(self, qa_report: dict[str, Any]) -> str:
        if qa_report.get("qa_status") == "passed":
            return "passed"

        failed_dimensions = set(qa_report.get("failed_dimensions") or [])
        if failed_dimensions & PLANNING_REWORK_DIMENSIONS:
            return "retry_research_development"
        if failed_dimensions & PRODUCTION_REWORK_DIMENSIONS:
            return "retry_production"
        return "retry_production"


class ConservativeQARerouteStrategy(QARerouteStrategy):
    name = "conservative"

    def determine_route_key(self, qa_report: dict[str, Any]) -> str:
        if qa_report.get("qa_status") == "passed":
            return "passed"
        return "retry_research_development"


class AggressiveQARerouteStrategy(QARerouteStrategy):
    name = "aggressive"

    def determine_route_key(self, qa_report: dict[str, Any]) -> str:
        if qa_report.get("qa_status") == "passed":
            return "passed"
        return "retry_production"


def build_default_qa_strategy_registry() -> dict[str, type[QARerouteStrategy]]:
    return {
        BalancedQARerouteStrategy.name: BalancedQARerouteStrategy,
        ConservativeQARerouteStrategy.name: ConservativeQARerouteStrategy,
        AggressiveQARerouteStrategy.name: AggressiveQARerouteStrategy,
    }


class QARerouteService:
    """Resolve QA rework targets from control-plane policy instead of hardcoded engine branches."""

    def __init__(
        self,
        control_plane,
        strategy_registry: Mapping[str, type[QARerouteStrategy]] | None = None,
    ) -> None:
        self.control_plane = control_plane
        self._strategy_registry = dict(strategy_registry or build_default_qa_strategy_registry())

    def register_strategy(self, strategy_class: type[QARerouteStrategy]) -> None:
        if not strategy_class.name:
            raise ValueError("QA reroute strategy must define a non-empty name")
        self._strategy_registry[strategy_class.name] = strategy_class

    def determine_reroute(self, qa_report: dict[str, Any]) -> QARerouteDecision:
        policy = self.control_plane.get_qa_reroute_policy()
        strategy_name = str(policy.get("strategy") or BalancedQARerouteStrategy.name)
        strategy_class = self._strategy_registry.get(strategy_name)
        if strategy_class is None:
            raise ValueError(f"Unsupported QA reroute strategy: {strategy_name}")

        route_key = strategy_class().determine_route_key(qa_report)
        mapping = dict(policy.get("mapping") or {})
        target = mapping.get(route_key)
        if not target:
            raise ValueError(f"QA reroute mapping missing target for route key: {route_key}")

        return QARerouteDecision(strategy=strategy_name, route_key=route_key, target=target)
