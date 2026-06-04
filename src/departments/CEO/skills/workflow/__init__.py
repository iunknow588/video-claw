from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from departments.CEO.services.control_plane import control_plane


@dataclass(slots=True)
class CEOPlan:
    run_plan: dict[str, Any]
    lead_route_list: list[str]
    dependency_order: list[str]
    policy: dict[str, Any]
    trace_id: str


class CEOWorkflowSkill:
    """Management-only CEO skill for the production system."""

    skill_name = "ceo.workflow"
    description = "CEO control plane for CFO/CIO + production-leader management, workflow ordering, monitoring, resource control, and evolution."
    tags = ["ceo", "workflow", "governance", "planning", "evolution"]
    parameters_schema = {
        "type": "object",
        "properties": {
            "domain": {"type": "string"},
            "platform": {"type": "string"},
            "trace_id": {"type": "string"},
            "name": {"type": "string"},
            "config": {"type": "object"},
            "graph_definition": {"type": "object"},
            "from_leader": {"type": "string"},
            "to_leader": {"type": "string"},
            "router_func": {"type": "string"},
            "mapping": {"type": "object"},
            "leader_name": {"type": "string"},
            "action_id": {"type": "string"},
            "action_type": {"type": "string"},
            "target_metric": {"type": "string"},
            "goal_value": {},
            "payload": {"type": "object"},
            "source": {"type": "string"},
            "reviewed_by": {"type": "string"},
            "decision_note": {"type": "string"},
            "status": {"type": "string"},
            "limit": {"type": "integer"},
            "proposal": {"type": "object"},
            "token_limit": {"type": "integer"},
            "resource_type": {"type": "string"},
            "amount": {},
            "version": {"type": "integer"},
            "company_status": {"type": "object"},
            "task_progress": {"type": "object"},
        },
        "required": [],
    }
    dependencies = [
        "lead.promotion",
        "lead.cho",
        "lead.cfo.estimate_cost",
        "lead.cfo.verify_balance",
        "lead.cfo.charge",
        "lead.cio.log",
        "lead.cio.store",
        "lead.research",
        "lead.analysis",
        "lead.research_development",
        "lead.production",
        "lead.qa",
        "lead.publish",
    ]

    def __init__(self) -> None:
        self.control_plane = control_plane

    def build_plan(self, input_bundle: dict[str, Any]) -> CEOPlan:
        domain = str(input_bundle.get("domain") or "")
        platform = str(input_bundle.get("platform") or "")
        trace_id = str(input_bundle.get("trace_id") or "")
        workflow = self.control_plane.get_workflow()
        route = self.control_plane.get_main_route()
        leader_snapshots = self.control_plane.list_leaders()
        run_plan = {
            "mission": self.control_plane.mission,
            "scope": self.control_plane.managed_scope,
            "domain": domain,
            "platform": platform,
            "workflow_version": workflow.get("version"),
            "graph_definition": workflow,
            "leader_snapshots": leader_snapshots,
            "resource_budgets": {
                item["name"]: item.get("token_limit", 0)
                for item in leader_snapshots
            },
        }
        return CEOPlan(
            run_plan=run_plan,
            lead_route_list=route,
            dependency_order=route,
            policy={
                "dispatch_mode": workflow.get("dispatch_mode", "graph"),
                "evolution_enabled": self.control_plane.evolution_enabled,
                "managed_scope": self.control_plane.managed_scope,
            },
            trace_id=trace_id,
        )

    def add_leader(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        leader = self.control_plane.add_leader(
            name=str(input_bundle.get("name") or ""),
            config=dict(input_bundle.get("config") or {}),
        )
        return {"leader": leader, "workflow": self.control_plane.get_workflow()}

    def remove_leader(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        leader = self.control_plane.remove_leader(name=str(input_bundle.get("name") or ""))
        return {"leader": leader, "workflow": self.control_plane.get_workflow()}

    def update_leader_config(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        leader = self.control_plane.update_leader_config(
            name=str(input_bundle.get("name") or ""),
            config=dict(input_bundle.get("config") or {}),
        )
        return {"leader": leader}

    def rollback_leader(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        leader = self.control_plane.rollback_leader(
            name=str(input_bundle.get("name") or ""),
            version=int(input_bundle.get("version") or 0),
        )
        return {"leader": leader}

    def get_leader_status(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        return {"leader": self.control_plane.get_leader_status(name=str(input_bundle.get("name") or ""))}

    def list_leaders(self, input_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
        leaders = self.control_plane.list_leaders()
        return {"leaders": leaders, "count": len(leaders)}

    def set_workflow(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        workflow = self.control_plane.set_workflow(
            graph_definition=dict(input_bundle.get("graph_definition") or {}),
        )
        return {"workflow": workflow}

    def get_workflow(self, input_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"workflow": self.control_plane.get_workflow()}

    def add_edge(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        workflow = self.control_plane.add_edge(
            from_leader=str(input_bundle.get("from_leader") or ""),
            to_leader=str(input_bundle.get("to_leader") or ""),
        )
        return {"workflow": workflow}

    def add_conditional_edge(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        workflow = self.control_plane.add_conditional_edge(
            from_leader=str(input_bundle.get("from_leader") or ""),
            router_func=str(input_bundle.get("router_func") or ""),
            mapping=dict(input_bundle.get("mapping") or {}),
        )
        return {"workflow": workflow}

    def get_config_action_capabilities(self, input_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.control_plane.get_config_action_capabilities()

    def list_config_actions(self, input_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
        bundle = dict(input_bundle or {})
        return self.control_plane.list_config_actions(
            status=str(bundle.get("status") or "") or None,
            leader_name=str(bundle.get("leader_name") or "") or None,
            limit=int(bundle.get("limit") or 50),
        )

    def get_config_action(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        return {"config_action": self.control_plane.get_config_action(action_id=str(input_bundle.get("action_id") or ""))}

    def create_config_action(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        return {
            "config_action": self.control_plane.create_config_action(
                leader_name=str(input_bundle.get("leader_name") or ""),
                action_type=str(input_bundle.get("action_type") or ""),
                target_metric=str(input_bundle.get("target_metric") or ""),
                goal_value=input_bundle.get("goal_value"),
                note=str(input_bundle.get("note") or "") or None,
                payload=dict(input_bundle.get("payload") or {}),
                source=str(input_bundle.get("source") or "ceo_manual"),
            )
        }

    def apply_config_action(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        return {
            "config_action": self.control_plane.apply_config_action(
                action_id=str(input_bundle.get("action_id") or ""),
                reviewed_by=str(input_bundle.get("reviewed_by") or "ceo"),
                decision_note=str(input_bundle.get("decision_note") or "") or None,
            )
        }

    def reject_config_action(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        return {
            "config_action": self.control_plane.reject_config_action(
                action_id=str(input_bundle.get("action_id") or ""),
                reviewed_by=str(input_bundle.get("reviewed_by") or "ceo"),
                decision_note=str(input_bundle.get("decision_note") or "") or None,
            )
        }

    def get_company_status(self, input_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "company_status": dict((input_bundle or {}).get("company_status") or {}),
            "mission": self.control_plane.mission,
        }

    def get_task_progress(self, input_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "task_progress": dict((input_bundle or {}).get("task_progress") or {}),
        }

    def request_leader_report(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        request = self.control_plane.request_leader_report(
            leader_name=str(input_bundle.get("leader_name") or ""),
        )
        return {"request": request}

    def approve_leader_change(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        approval = self.control_plane.approve_leader_change(
            leader_name=str(input_bundle.get("leader_name") or ""),
            proposal=dict(input_bundle.get("proposal") or {}),
        )
        return {"approval": approval}

    def set_leader_budget(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        leader = self.control_plane.set_leader_budget(
            leader_name=str(input_bundle.get("leader_name") or ""),
            token_limit=int(input_bundle.get("token_limit") or 0),
        )
        return {"leader": leader}

    def adjust_resource_allocation(self, input_bundle: dict[str, Any]) -> dict[str, Any]:
        leader = self.control_plane.adjust_resource_allocation(
            leader_name=str(input_bundle.get("leader_name") or ""),
            resource_type=str(input_bundle.get("resource_type") or ""),
            amount=input_bundle.get("amount"),
        )
        return {"leader": leader}

    def enable_evolution(self, input_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.control_plane.enable_evolution()

    def disable_evolution(self, input_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.control_plane.disable_evolution()

    def evolution_cycle(self, input_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
        bundle = dict(input_bundle or {})
        return self.control_plane.evolution_cycle(company_status=bundle.get("company_status"))
