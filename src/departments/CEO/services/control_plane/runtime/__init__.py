from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from departments.CEO.leaders import build_department_leader
from departments.CEO.leaders.base import ManagedLeader
from departments.CEO.leaders.organization import build_org_title_registry
from departments.CEO.services.control_plane.defaults import (
    get_control_plane_mission,
    get_control_plane_scope,
    get_default_leaders,
    get_default_workflow,
)


class CEOControlPlane:
    mission = ""
    managed_scope = ""
    DISPATCH_MODE_OPTIONS = ["graph"]
    QA_REROUTE_STRATEGY_OPTIONS = ["aggressive", "balanced", "conservative"]
    CONFIG_ACTION_CAPABILITIES = [
        {
            "action_type": "update_leader_config",
            "label": "Update Leader Config",
            "description": "Patch a leader configuration block, including model, prompt, aliases, tags, and resource allocations.",
            "payload_schema": {
                "config": {
                    "display_name": "optional string",
                    "description": "optional string",
                    "model": "optional string",
                    "system_prompt": "optional string",
                    "bound_tools": ["optional tool ids"],
                    "aliases": ["optional aliases"],
                    "tags": ["optional tags"],
                    "token_limit": "optional integer",
                    "resource_allocations": {"any_key": "any_value"},
                    "organization_profile": {"any_key": "any_value"},
                }
            },
        },
        {
            "action_type": "set_budget",
            "label": "Set Token Budget",
            "description": "Change the token budget owned by a leader.",
            "payload_schema": {
                "token_limit": "required integer",
            },
        },
        {
            "action_type": "adjust_resource_allocation",
            "label": "Adjust Resource Allocation",
            "description": "Change a single resource allocation key without replacing the whole leader config.",
            "payload_schema": {
                "resource_type": "required string",
                "amount": "required any",
            },
        },
    ]

    def __init__(self) -> None:
        self.reset_defaults()

    def reset_defaults(self) -> None:
        self.__class__.mission = get_control_plane_mission()
        self.__class__.managed_scope = get_control_plane_scope()
        default_leaders = get_default_leaders()
        default_workflow = get_default_workflow()
        self._leaders = {
            name: self._build_leader_record(name=name, config=config)
            for name, config in default_leaders.items()
        }
        self._workflow = deepcopy(default_workflow)
        self.evolution_enabled = False
        self.config_actions: list[dict[str, Any]] = []
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
                    "strategy": edge.get("strategy") or "balanced",
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
        edge = {
            "from": source,
            "router_func": router_func,
            "strategy": "balanced",
            "mapping": normalized_mapping,
        }
        existing = next(
            (
                item
                for item in self._workflow["conditional_edges"]
                if item.get("from") == source and item.get("router_func") == router_func
            ),
            None,
        )
        if existing:
            existing["strategy"] = edge["strategy"]
            existing["mapping"] = normalized_mapping
        else:
            self._workflow["conditional_edges"].append(edge)
        return self.get_workflow()

    def get_config_action_capabilities(self) -> dict[str, Any]:
        return {
            "capabilities": deepcopy(self.CONFIG_ACTION_CAPABILITIES),
            "command_format": {
                "leader_name": "required string, managed leader id such as lead.production",
                "action_type": "required string, supported values: update_leader_config / set_budget / adjust_resource_allocation",
                "target_metric": "required string, governance metric to optimize",
                "goal_value": "optional number|string, target value for approval review",
                "note": "optional string, manual review note",
                "payload": "required object, shape depends on action_type",
                "source": "optional string, defaults to ceo_manual",
            },
            "status_flow": ["proposed", "applied", "rejected"],
            "review_policy": {
                "proposed": "action has been created and is waiting for CEO review",
                "applied": "action has been approved and applied to leader configuration",
                "rejected": "action has been reviewed and rejected",
            },
            "examples": [
                {
                    "leader_name": "lead.production",
                    "action_type": "set_budget",
                    "target_metric": "workflow_success_rate",
                    "goal_value": 0.92,
                    "note": "Raise production budget for a stability trial.",
                    "payload": {"token_limit": 24000},
                    "source": "ceo_manual",
                },
                {
                    "leader_name": "lead.qa",
                    "action_type": "adjust_resource_allocation",
                    "target_metric": "qa_pass_rate",
                    "goal_value": 0.97,
                    "note": "Increase QA review priority for the next cycle.",
                    "payload": {"resource_type": "review_priority", "amount": "critical"},
                    "source": "ceo_manual",
                },
            ],
        }

    def list_config_actions(
        self,
        *,
        status: str | None = None,
        leader_name: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        items = list(self.config_actions)
        if status:
            items = [item for item in items if str(item.get("status") or "") == status]
        if leader_name:
            normalized = self._normalize_leader_name(leader_name)
            items = [item for item in items if item.get("leader_name") == normalized]
        items.sort(key=lambda item: item.get("created_at") or datetime.min.replace(tzinfo=UTC), reverse=True)
        limited_items = deepcopy(items[: max(1, int(limit))])
        return {
            "config_actions": limited_items,
            "count": len(limited_items),
            "status_summary": self._summarize_config_actions(),
            "available_statuses": ["proposed", "applied", "rejected"],
        }

    def get_config_action(self, *, action_id: str) -> dict[str, Any]:
        for item in self.config_actions:
            if item.get("action_id") == action_id:
                return deepcopy(item)
        raise ValueError(f"Unknown config action: {action_id}")

    def create_config_action(
        self,
        *,
        leader_name: str,
        action_type: str = "update_leader_config",
        target_metric: str,
        goal_value: Any,
        note: str | None = None,
        payload: dict[str, Any] | None = None,
        source: str = "ceo_manual",
    ) -> dict[str, Any]:
        record = self._require_leader(leader_name)
        normalized_payload = self._normalize_config_action_payload(action_type=action_type, payload=payload or {})
        action = {
            "action_id": uuid4().hex,
            "leader_name": record.name,
            "leader_display_name": record.display_name,
            "action_type": action_type,
            "target_metric": target_metric,
            "goal_value": goal_value,
            "status": "proposed",
            "note": note,
            "payload": normalized_payload,
            "source": source,
            "created_at": datetime.now(UTC),
            "reviewed_at": None,
            "reviewed_by": None,
            "decision_note": None,
        }
        leader_event = record.accept_command(command_type="config_action", payload=action)
        action["leader_event"] = leader_event
        self.config_actions.append(deepcopy(action))
        return action

    def apply_config_action(
        self,
        *,
        action_id: str,
        reviewed_by: str = "ceo",
        decision_note: str | None = None,
    ) -> dict[str, Any]:
        action = self._require_mutable_config_action(action_id)
        if action.get("status") != "proposed":
            raise ValueError(f"Config action {action_id} is already {action.get('status')}")

        leader_snapshot = self._apply_config_action_payload(action)
        action["status"] = "applied"
        action["reviewed_at"] = datetime.now(UTC)
        action["reviewed_by"] = reviewed_by
        action["decision_note"] = decision_note
        action["applied_snapshot"] = deepcopy(leader_snapshot)

        record = self._require_leader(str(action.get("leader_name") or ""))
        record.lifecycle_events.append(
            self._event(
                "config_action_applied",
                {
                    "action_id": action_id,
                    "reviewed_by": reviewed_by,
                    "decision_note": decision_note,
                },
            )
        )
        return deepcopy(action)

    def reject_config_action(
        self,
        *,
        action_id: str,
        reviewed_by: str = "ceo",
        decision_note: str | None = None,
    ) -> dict[str, Any]:
        action = self._require_mutable_config_action(action_id)
        if action.get("status") != "proposed":
            raise ValueError(f"Config action {action_id} is already {action.get('status')}")

        action["status"] = "rejected"
        action["reviewed_at"] = datetime.now(UTC)
        action["reviewed_by"] = reviewed_by
        action["decision_note"] = decision_note

        record = self._require_leader(str(action.get("leader_name") or ""))
        record.lifecycle_events.append(
            self._event(
                "config_action_rejected",
                {
                    "action_id": action_id,
                    "reviewed_by": reviewed_by,
                    "decision_note": decision_note,
                },
            )
        )
        return deepcopy(action)

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
        issued_config_actions: list[dict[str, Any]] = []

        qa_pass_rate = float(quality_metrics.get("qa_pass_rate") or 0.0)
        if qa_pass_rate and qa_pass_rate < 0.95:
            issued_config_actions.append(
                self.create_config_action(
                    leader_name="lead.qa",
                    action_type="update_leader_config",
                    target_metric="qa_pass_rate",
                    goal_value=0.95,
                    note="Tighten QA gate and improve reroute precision through CEO-managed configuration.",
                    payload={
                        "config": {
                            "resource_allocations": {"review_priority": "high", "reroute_precision_mode": "strict"},
                        }
                    },
                    source="evolution_cycle",
                )
            )

        success_rate = float(run_metrics.get("success_rate") or 0.0)
        if success_rate and success_rate < 0.9:
            issued_config_actions.append(
                self.create_config_action(
                    leader_name="lead.production",
                    action_type="update_leader_config",
                    target_metric="workflow_success_rate",
                    goal_value=0.9,
                    note="Increase production stability through CEO-managed production configuration.",
                    payload={
                        "config": {
                            "resource_allocations": {"stability_mode": "high", "retry_budget": 2},
                        }
                    },
                    source="evolution_cycle",
                )
            )

        budget_ratio = float((snapshot.get("operations_summary") or {}).get("budget_usage_ratio") or 0.0)
        if budget_ratio > 1.0:
            issued_config_actions.append(
                self.create_config_action(
                    leader_name="lead.cfo",
                    action_type="update_leader_config",
                    target_metric="budget_guardrail",
                    goal_value=1.0,
                    note="Tighten budget validation and charging guardrails through CEO-managed finance configuration.",
                    payload={
                        "config": {
                            "resource_allocations": {"guardrail_mode": "strict"},
                        }
                    },
                    source="evolution_cycle",
                )
            )
            issued_config_actions.append(
                self.create_config_action(
                    leader_name="lead.research_development",
                    action_type="update_leader_config",
                    target_metric="token_efficiency",
                    goal_value=0.85,
                    note="Reduce ineffective prompt-token spend through CEO-managed planning configuration.",
                    payload={
                        "config": {
                            "resource_allocations": {
                                "token_budget_mode": "tight",
                                "prompt_validation_level": "strict",
                            },
                        }
                    },
                    source="evolution_cycle",
                )
            )

        return {
            "evolution_enabled": self.evolution_enabled,
            "observed_run_metrics": run_metrics,
            "observed_quality_metrics": quality_metrics,
            "issued_config_actions": issued_config_actions,
            "message": (
                "CEO completed an observe -> analyze -> config cycle."
                if issued_config_actions
                else "CEO completed an observe -> analyze -> config cycle with no new configuration actions."
            ),
        }

    def get_main_route(self) -> list[str]:
        route = [name for name in self._workflow.get("main_route", []) if self._is_active(name)]
        return route or list(get_default_workflow().get("main_route", []))

    def get_non_workflow_leaders(self) -> list[str]:
        route = set(self.get_main_route())
        return [
            record.name
            for record in sorted(self._leaders.values(), key=lambda item: item.name)
            if record.status == "active" and record.name not in route
        ]

    def get_title_registry(self) -> dict[str, list[dict[str, Any]]]:
        return build_org_title_registry()

    def get_qa_reroute_policy(self) -> dict[str, Any]:
        for edge in self._workflow.get("conditional_edges", []):
            if edge.get("from") == "lead.qa":
                return {
                    "strategy": edge.get("strategy") or "balanced",
                    "mapping": dict(edge.get("mapping") or {}),
                }
        for edge in get_default_workflow().get("conditional_edges", []):
            if edge.get("from") == "lead.qa":
                return {
                    "strategy": edge.get("strategy") or "balanced",
                    "mapping": dict(edge.get("mapping") or {}),
                }
        return {
            "strategy": "balanced",
            "mapping": {
                "passed": "lead.publish",
                "retry_production": "lead.production",
                "retry_research_development": "lead.research_development",
            },
        }

    def get_qa_rework_policy(self) -> dict[str, Any]:
        workflow = self._workflow or {}
        defaults = get_default_workflow()
        current_policy = dict(workflow.get("qa_rework") or {})
        default_policy = dict(defaults.get("qa_rework") or {})
        merged = {**default_policy, **current_policy}
        merged.setdefault("max_attempts", 1)
        return merged

    def get_runtime_controls(self) -> dict[str, Any]:
        reroute_policy = self.get_qa_reroute_policy()
        qa_rework_policy = self.get_qa_rework_policy()
        return {
            "evolution_enabled": self.evolution_enabled,
            "dispatch_mode": str(self._workflow.get("dispatch_mode") or "graph"),
            "dispatch_mode_options": list(self.DISPATCH_MODE_OPTIONS),
            "qa_rework_max_attempts": int(qa_rework_policy.get("max_attempts") or 0),
            "qa_reroute_strategy": str(reroute_policy.get("strategy") or "balanced"),
            "qa_reroute_strategy_options": list(self.QA_REROUTE_STRATEGY_OPTIONS),
            "qa_reroute_mapping": dict(reroute_policy.get("mapping") or {}),
        }

    def update_runtime_controls(
        self,
        *,
        evolution_enabled: bool | None = None,
        dispatch_mode: str | None = None,
        qa_rework_max_attempts: int | None = None,
        qa_reroute_strategy: str | None = None,
    ) -> dict[str, Any]:
        if evolution_enabled is not None:
            self.evolution_enabled = bool(evolution_enabled)

        if dispatch_mode is not None:
            normalized_dispatch_mode = str(dispatch_mode).strip() or "graph"
            if normalized_dispatch_mode not in self.DISPATCH_MODE_OPTIONS:
                raise ValueError(f"Unsupported dispatch mode: {normalized_dispatch_mode}")
            self._workflow["dispatch_mode"] = normalized_dispatch_mode

        if qa_rework_max_attempts is not None:
            if int(qa_rework_max_attempts) < 0:
                raise ValueError("QA rework max attempts must be >= 0")
            self._workflow["qa_rework"] = {
                **dict(self._workflow.get("qa_rework") or {}),
                "max_attempts": int(qa_rework_max_attempts),
            }

        if qa_reroute_strategy is not None:
            normalized_strategy = str(qa_reroute_strategy).strip() or "balanced"
            if normalized_strategy not in self.QA_REROUTE_STRATEGY_OPTIONS:
                raise ValueError(f"Unsupported QA reroute strategy: {normalized_strategy}")

            updated = False
            for edge in self._workflow.get("conditional_edges", []):
                if edge.get("from") == "lead.qa":
                    edge["strategy"] = normalized_strategy
                    updated = True
                    break

            if not updated:
                default_mapping = self.get_qa_reroute_policy().get("mapping") or {
                    "passed": "lead.publish",
                    "retry_production": "lead.production",
                    "retry_research_development": "lead.research_development",
                }
                self._workflow.setdefault("conditional_edges", []).append(
                    {
                        "from": "lead.qa",
                        "router_func": "route",
                        "strategy": normalized_strategy,
                        "mapping": dict(default_mapping),
                    }
                )

        return self.get_runtime_controls()

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
        payload["pending_config_actions"] = len(
            [
                item
                for item in self.config_actions
                if item.get("leader_name") == record.name and item.get("status") == "proposed"
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

    def _normalize_config_action_payload(self, *, action_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if action_type == "update_leader_config":
            config = dict(payload.get("config") or {})
            if not config:
                raise ValueError("update_leader_config action requires payload.config")
            return {"config": config}
        if action_type == "set_budget":
            if "token_limit" not in payload:
                raise ValueError("set_budget action requires payload.token_limit")
            return {"token_limit": int(payload.get("token_limit") or 0)}
        if action_type == "adjust_resource_allocation":
            resource_type = str(payload.get("resource_type") or "").strip()
            if not resource_type:
                raise ValueError("adjust_resource_allocation action requires payload.resource_type")
            if "amount" not in payload:
                raise ValueError("adjust_resource_allocation action requires payload.amount")
            return {
                "resource_type": resource_type,
                "amount": payload.get("amount"),
            }
        raise ValueError(f"Unsupported config action type: {action_type}")

    def _apply_config_action_payload(self, action: dict[str, Any]) -> dict[str, Any]:
        leader_name = str(action.get("leader_name") or "")
        action_type = str(action.get("action_type") or "")
        payload = dict(action.get("payload") or {})
        if action_type == "update_leader_config":
            return self.update_leader_config(name=leader_name, config=dict(payload.get("config") or {}))
        if action_type == "set_budget":
            return self.set_leader_budget(leader_name=leader_name, token_limit=int(payload.get("token_limit") or 0))
        if action_type == "adjust_resource_allocation":
            return self.adjust_resource_allocation(
                leader_name=leader_name,
                resource_type=str(payload.get("resource_type") or ""),
                amount=payload.get("amount"),
            )
        raise ValueError(f"Unsupported config action type: {action_type}")

    def _require_mutable_config_action(self, action_id: str) -> dict[str, Any]:
        for item in self.config_actions:
            if item.get("action_id") == action_id:
                return item
        raise ValueError(f"Unknown config action: {action_id}")

    def _summarize_config_actions(self) -> dict[str, int]:
        summary = {
            "proposed": 0,
            "applied": 0,
            "rejected": 0,
            "total": len(self.config_actions),
        }
        for item in self.config_actions:
            status = str(item.get("status") or "")
            if status in summary:
                summary[status] += 1
        return summary

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
