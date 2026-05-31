from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.CEO.leaders import build_department_leader
from app.leaders.base import ManagedLeader
from app.leaders.organization import build_org_title_registry
from app.services.ceo_control_plane.defaults import DEFAULT_LEADERS, DEFAULT_WORKFLOW


class CEOControlPlane:
    mission = ""
    managed_scope = ""

    def __init__(self) -> None:
        self.reset_defaults()

    def reset_defaults(self) -> None:
        self._leaders = {
            name: self._build_leader_record(name=name, config=config)
            for name, config in DEFAULT_LEADERS.items()
        }
        self._workflow = deepcopy(DEFAULT_WORKFLOW)
        self.evolution_enabled = False
        self.optimize_commands: list[dict[str, Any]] = []
        self.report_requests: list[dict[str, Any]] = []
        self.change_approvals: list[dict[str, Any]] = []

    def list_leaders(self) -> list[dict[str, Any]]:
        return [
            self._serialize_leader(record)
            for record in sorted(self._leaders.values(), key=lambda item: item.name)
            if record.status == "active"
        ]

    def add_leader(self, *, name: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        leader_name = self._normalize_new_leader_name(name)
        if leader_name in self._leaders and self._leaders[leader_name].status == "active":
            raise ValueError(f"Leader {leader_name} already exists")
        record = self._build_leader_record(name=leader_name, config=config or {})
        record.lifecycle_events.append(self._event("added", {"config": config or {}}))
        self._leaders[leader_name] = record
        return self._serialize_leader(record)

    def remove_leader(self, *, name: str) -> dict[str, Any]:
        record = self._require_leader(name)
        record.lifecycle_events.append(self._event("removed"))
        record.status = "removed"
        self._workflow["main_route"] = [item for item in self._workflow["main_route"] if item != record.name]
        self._workflow["edges"] = [
            edge
            for edge in self._workflow["edges"]
            if edge.get("from") != record.name and edge.get("to") != record.name
        ]
        self._workflow["conditional_edges"] = [
            edge
            for edge in self._workflow["conditional_edges"]
            if edge.get("from") != record.name and record.name not in (edge.get("mapping") or {}).values()
        ]
        return self._serialize_leader(record)

    def update_leader_config(self, *, name: str, config: dict[str, Any]) -> dict[str, Any]:
        record = self._require_leader(name)
        record.remember_version()
        record.apply_config(config)
        record.version += 1
        record.lifecycle_events.append(self._event("updated", {"config": config}))
        return self._serialize_leader(record)

    def rollback_leader(self, *, name: str, version: int) -> dict[str, Any]:
        record = self._require_leader(name)
        snapshot = next((item for item in reversed(record.version_history) if item["version"] == version), None)
        if not snapshot:
            raise ValueError(f"Leader {record.name} has no stored version {version}")
        record.restore(snapshot)
        record.lifecycle_events.append(self._event("rolled_back", {"target_version": version}))
        return self._serialize_leader(record)

    def get_leader_status(self, *, name: str) -> dict[str, Any]:
        return self._serialize_leader(self._require_leader(name))

    def build_leader_periodic_report(self, *, name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._require_leader(name).build_periodic_report(context or {})

    def set_workflow(self, *, graph_definition: dict[str, Any]) -> dict[str, Any]:
        main_route = [self._normalize_leader_name(name) for name in list(graph_definition.get("main_route") or [])]
        if not main_route:
            raise ValueError("Workflow main_route must not be empty")
        self._validate_route(main_route)

        edges: list[dict[str, str]] = []
        conditional_edges: list[dict[str, Any]] = []
        for edge in list(graph_definition.get("edges") or []):
            source = self._normalize_leader_name(edge.get("from"))
            target = self._normalize_leader_name(edge.get("to"))
            self._validate_edge(source, target)
            edges.append({"from": source, "to": target})
        for edge in list(graph_definition.get("conditional_edges") or []):
            source = self._normalize_leader_name(edge.get("from"))
            mapping = {
                key: self._normalize_leader_name(value)
                for key, value in (edge.get("mapping") or {}).items()
            }
            self._validate_conditional_edge(source, mapping)
            conditional_edges.append(
                {
                    "from": source,
                    "router_func": edge.get("router_func") or "route",
                    "mapping": mapping,
                }
            )

        self._workflow = {
            "version": int(self._workflow.get("version", 1)) + 1,
            "dispatch_mode": graph_definition.get("dispatch_mode") or "graph",
            "main_route": main_route,
            "edges": edges,
            "conditional_edges": conditional_edges,
            "parallel_groups": list(graph_definition.get("parallel_groups") or []),
        }
        return self.get_workflow()

    def get_workflow(self) -> dict[str, Any]:
        return deepcopy(self._workflow)

    def add_edge(self, *, from_leader: str, to_leader: str) -> dict[str, Any]:
        source = self._normalize_leader_name(from_leader)
        target = self._normalize_leader_name(to_leader)
        self._validate_edge(source, target)
        edge = {"from": source, "to": target}
        if edge not in self._workflow["edges"]:
            self._workflow["edges"].append(edge)
        return self.get_workflow()

    def add_conditional_edge(
        self,
        *,
        from_leader: str,
        router_func: str,
        mapping: dict[str, str],
    ) -> dict[str, Any]:
        source = self._normalize_leader_name(from_leader)
        normalized_mapping = {key: self._normalize_leader_name(value) for key, value in mapping.items()}
        self._validate_conditional_edge(source, normalized_mapping)
        edge = {"from": source, "router_func": router_func, "mapping": normalized_mapping}
        existing = next(
            (
                item
                for item in self._workflow["conditional_edges"]
                if item.get("from") == source and item.get("router_func") == router_func
            ),
            None,
        )
        if existing:
            existing["mapping"] = normalized_mapping
        else:
            self._workflow["conditional_edges"].append(edge)
        return self.get_workflow()

    def issue_optimize_command(
        self,
        *,
        leader_name: str,
        target_metric: str,
        goal_value: Any,
        note: str | None = None,
    ) -> dict[str, Any]:
        record = self._require_leader(leader_name)
        command = {
            "command_id": uuid4().hex,
            "leader_name": record.name,
            "leader_display_name": record.display_name,
            "target_metric": target_metric,
            "goal_value": goal_value,
            "status": "issued",
            "note": note,
            "created_at": datetime.now(UTC),
        }
        leader_event = record.accept_command(command_type="optimize", payload=command)
        command["leader_event"] = leader_event
        self.optimize_commands.append(deepcopy(command))
        return command

    def request_leader_report(self, *, leader_name: str) -> dict[str, Any]:
        record = self._require_leader(leader_name)
        request = {
            "request_id": uuid4().hex,
            "leader_name": record.name,
            "leader_display_name": record.display_name,
            "status": "requested",
            "created_at": datetime.now(UTC),
        }
        request["report_preview"] = record.build_report()
        record.lifecycle_events.append(self._event("report_requested", request))
        self.report_requests.append(deepcopy(request))
        return request

    def approve_leader_change(self, *, leader_name: str, proposal: dict[str, Any]) -> dict[str, Any]:
        record = self._require_leader(leader_name)
        normalized_proposal = record.propose_change(proposal)
        approval = {
            "approval_id": uuid4().hex,
            "leader_name": record.name,
            "leader_display_name": record.display_name,
            "proposal": normalized_proposal,
            "status": "approved",
            "created_at": datetime.now(UTC),
        }
        record.lifecycle_events.append(self._event("change_approved", approval))
        self.change_approvals.append(deepcopy(approval))
        return approval

    def set_leader_budget(self, *, leader_name: str, token_limit: int) -> dict[str, Any]:
        record = self._require_leader(leader_name)
        record.remember_version()
        record.token_limit = int(token_limit)
        record.resource_allocations["token_limit"] = int(token_limit)
        record.version += 1
        record.lifecycle_events.append(self._event("budget_updated", {"token_limit": int(token_limit)}))
        return self._serialize_leader(record)

    def adjust_resource_allocation(
        self,
        *,
        leader_name: str,
        resource_type: str,
        amount: Any,
    ) -> dict[str, Any]:
        record = self._require_leader(leader_name)
        record.remember_version()
        record.resource_allocations[resource_type] = amount
        record.version += 1
        record.lifecycle_events.append(
            self._event("resource_updated", {"resource_type": resource_type, "amount": amount})
        )
        return self._serialize_leader(record)

    def enable_evolution(self) -> dict[str, Any]:
        self.evolution_enabled = True
        return {"evolution_enabled": True, "message": "CEO evolution mode enabled."}

    def disable_evolution(self) -> dict[str, Any]:
        self.evolution_enabled = False
        return {"evolution_enabled": False, "message": "CEO evolution mode disabled."}

    def evolution_cycle(self, *, company_status: dict[str, Any] | None = None) -> dict[str, Any]:
        snapshot = company_status or {}
        run_metrics = snapshot.get("run_metrics") or {}
        quality_metrics = snapshot.get("quality_metrics") or {}
        issued_commands: list[dict[str, Any]] = []

        qa_pass_rate = float(quality_metrics.get("qa_pass_rate") or 0.0)
        if qa_pass_rate and qa_pass_rate < 0.95:
            issued_commands.append(
                self.issue_optimize_command(
                    leader_name="lead.qa",
                    target_metric="qa_pass_rate",
                    goal_value=0.95,
                    note="Raise QA pass rate and improve reroute precision.",
                )
            )

        success_rate = float(run_metrics.get("success_rate") or 0.0)
        if success_rate and success_rate < 0.9:
            issued_commands.append(
                self.issue_optimize_command(
                    leader_name="lead.production",
                    target_metric="workflow_success_rate",
                    goal_value=0.9,
                    note="Raise production stability and reduce delivery failures.",
                )
            )

        budget_ratio = float((snapshot.get("operations_summary") or {}).get("budget_usage_ratio") or 0.0)
        if budget_ratio > 1.0:
            issued_commands.append(
                self.issue_optimize_command(
                    leader_name="lead.cfo",
                    target_metric="budget_guardrail",
                    goal_value=1.0,
                    note="Tighten budget validation and charging guardrails.",
                )
            )
            issued_commands.append(
                self.issue_optimize_command(
                    leader_name="lead.research_development",
                    target_metric="token_efficiency",
                    goal_value=0.85,
                    note="Reduce ineffective prompt-token spend.",
                )
            )

        return {
            "evolution_enabled": self.evolution_enabled,
            "observed_run_metrics": run_metrics,
            "observed_quality_metrics": quality_metrics,
            "issued_commands": issued_commands,
            "message": (
                "CEO completed an observe -> analyze -> command cycle."
                if issued_commands
                else "CEO completed an observe -> analyze -> command cycle with no new actions issued."
            ),
        }

    def get_main_route(self) -> list[str]:
        route = [name for name in self._workflow.get("main_route", []) if self._is_active(name)]
        return route or list(DEFAULT_WORKFLOW.get("main_route", []))

    def get_non_workflow_leaders(self) -> list[str]:
        route = set(self.get_main_route())
        return [
            record.name
            for record in sorted(self._leaders.values(), key=lambda item: item.name)
            if record.status == "active" and record.name not in route
        ]

    def get_title_registry(self) -> dict[str, list[dict[str, Any]]]:
        return build_org_title_registry()

    def get_qa_reroute_mapping(self) -> dict[str, str]:
        for edge in self._workflow.get("conditional_edges", []):
            if edge.get("from") == "lead.qa":
                return dict(edge.get("mapping") or {})
        return {
            "passed": "lead.publish",
            "retry_production": "lead.production",
            "retry_research_development": "lead.research_development",
        }

    def _build_leader_record(self, *, name: str, config: dict[str, Any]) -> ManagedLeader:
        return build_department_leader(name, config)

    def _serialize_leader(self, record: ManagedLeader) -> dict[str, Any]:
        payload = record.get_status()
        in_main_workflow_route = record.name in set(self.get_main_route())
        payload["management_scope"] = {
            "direct_ceo_managed": True,
            "reports_to_ceo": True,
            "in_main_workflow_route": in_main_workflow_route,
            "user_facing": record.name == "lead.promotion",
            "public_agent_managed": record.name == "lead.cho",
            "external_api_managed": record.name == "lead.publish",
            "workflow_role": "main_route" if in_main_workflow_route else "support_department",
        }
        payload["report_template"] = record.build_report()
        payload["periodic_report_template"] = record.build_periodic_report()
        payload["pending_optimize_commands"] = len(
            [
                item
                for item in self.optimize_commands
                if item.get("leader_name") == record.name and item.get("status") == "issued"
            ]
        )
        payload["pending_report_requests"] = len(
            [
                item
                for item in self.report_requests
                if item.get("leader_name") == record.name and item.get("status") == "requested"
            ]
        )
        return payload

    def _normalize_new_leader_name(self, name: str) -> str:
        clean = str(name or "").strip()
        if not clean:
            raise ValueError("Leader name is required")
        if clean.startswith("lead.") or clean == "ceo.workflow":
            return clean
        return f"lead.{clean}"

    def _normalize_leader_name(self, name: str) -> str:
        clean = str(name or "").strip()
        if not clean:
            raise ValueError("Leader name is required")
        lowered = clean.lower()
        for record in self._leaders.values():
            if record.accepts_alias(lowered):
                return record.name
        if clean in self._leaders:
            return clean
        raise ValueError(f"Unknown leader: {name}")

    def _require_leader(self, name: str) -> ManagedLeader:
        leader_name = self._normalize_leader_name(name)
        record = self._leaders.get(leader_name)
        if not record:
            raise ValueError(f"Unknown leader: {name}")
        return record

    def _validate_route(self, main_route: list[str]) -> None:
        inactive = [name for name in main_route if not self._is_active(name)]
        if inactive:
            raise ValueError(f"Workflow contains inactive leaders: {inactive}")

    def _validate_edge(self, source: str | None, target: str | None) -> None:
        if not source or not target:
            raise ValueError("Edge requires both from and to leaders")
        source_name = self._normalize_leader_name(source)
        target_name = self._normalize_leader_name(target)
        if not self._is_active(source_name) or not self._is_active(target_name):
            raise ValueError("Edge can only target active leaders")

    def _validate_conditional_edge(self, source: str | None, mapping: dict[str, str]) -> None:
        if not source or not mapping:
            raise ValueError("Conditional edge requires source and mapping")
        source_name = self._normalize_leader_name(source)
        if not self._is_active(source_name):
            raise ValueError("Conditional edge source must be active")
        for target in mapping.values():
            if not self._is_active(target):
                raise ValueError(f"Conditional edge target must be active: {target}")

    def _is_active(self, leader_name: str) -> bool:
        record = self._leaders.get(leader_name)
        return bool(record and record.status == "active")

    def _event(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "event_type": event_type,
            "payload": payload or {},
            "created_at": datetime.now(UTC),
        }
