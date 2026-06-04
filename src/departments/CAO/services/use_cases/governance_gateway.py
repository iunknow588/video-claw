from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from departments.CEO.services.control import CEOControlService


class GovernanceGatewayUseCase:
    """CAO-owned governance gateway backed by the internal CEO control service."""

    def __init__(self, session: AsyncSession):
        self.service = CEOControlService(session)

    async def get_company_status(self) -> dict:
        return await self.service.get_company_status()

    async def get_workflow(self) -> dict:
        return await self.service.get_workflow()

    async def set_workflow(self, graph_definition: dict) -> dict:
        return await self.service.set_workflow(graph_definition)

    async def add_edge(self, from_leader: str, to_leader: str) -> dict:
        return await self.service.add_edge(from_leader, to_leader)

    async def add_conditional_edge(
        self,
        from_leader: str,
        router_func: str,
        mapping: dict,
    ) -> dict:
        return await self.service.add_conditional_edge(from_leader, router_func, mapping)

    async def list_leaders(self) -> dict:
        return await self.service.list_leaders()

    async def add_leader(self, name: str, config: dict) -> dict:
        return await self.service.add_leader(name, config)

    async def get_leader_status(self, leader_name: str) -> dict:
        return await self.service.get_leader_status(leader_name)

    async def update_leader_config(self, leader_name: str, config: dict) -> dict:
        return await self.service.update_leader_config(leader_name, config)

    async def remove_leader(self, leader_name: str) -> dict:
        return await self.service.remove_leader(leader_name)

    async def rollback_leader(self, leader_name: str, version: int) -> dict:
        return await self.service.rollback_leader(leader_name, version)

    async def request_leader_report(self, leader_name: str) -> dict:
        return await self.service.request_leader_report(leader_name)

    async def get_latest_leader_report(self, leader_name: str, report_type: str | None) -> dict:
        return await self.service.get_latest_leader_report(leader_name=leader_name, report_type=report_type)

    async def list_leader_reports(
        self,
        *,
        leader_name: str | None,
        report_type: str | None,
        limit: int,
    ) -> dict:
        return await self.service.list_leader_reports(
            leader_name=leader_name,
            report_type=report_type,
            limit=limit,
        )

    async def approve_leader_change(self, leader_name: str, proposal: dict) -> dict:
        return await self.service.approve_leader_change(leader_name, proposal)

    async def set_leader_budget(self, leader_name: str, token_limit: int) -> dict:
        return await self.service.set_leader_budget(leader_name, token_limit)

    async def adjust_resource_allocation(
        self,
        leader_name: str,
        resource_type: str,
        amount: int,
    ) -> dict:
        return await self.service.adjust_resource_allocation(leader_name, resource_type, amount)

    async def get_config_action_capabilities(self) -> dict:
        return await self.service.get_config_action_capabilities()

    async def list_config_actions(
        self,
        *,
        status: str | None = None,
        leader_name: str | None = None,
        limit: int = 50,
    ) -> dict:
        return await self.service.list_config_actions(status=status, leader_name=leader_name, limit=limit)

    async def get_config_action(self, action_id: str) -> dict:
        return await self.service.get_config_action(action_id)

    async def create_config_action(
        self,
        *,
        leader_name: str,
        action_type: str,
        target_metric: str,
        goal_value: float | int | str | None,
        note: str | None = None,
        payload: dict | None = None,
        source: str = "ceo_manual",
    ) -> dict:
        return await self.service.create_config_action(
            leader_name=leader_name,
            action_type=action_type,
            target_metric=target_metric,
            goal_value=goal_value,
            note=note,
            payload=payload,
            source=source,
        )

    async def apply_config_action(
        self,
        *,
        action_id: str,
        reviewed_by: str = "ceo",
        decision_note: str | None = None,
    ) -> dict:
        return await self.service.apply_config_action(
            action_id=action_id,
            reviewed_by=reviewed_by,
            decision_note=decision_note,
        )

    async def reject_config_action(
        self,
        *,
        action_id: str,
        reviewed_by: str = "ceo",
        decision_note: str | None = None,
    ) -> dict:
        return await self.service.reject_config_action(
            action_id=action_id,
            reviewed_by=reviewed_by,
            decision_note=decision_note,
        )

    async def get_task_progress(self, workflow_run_id: str) -> dict:
        return await self.service.get_task_progress(workflow_run_id)

    async def enable_evolution(self) -> dict:
        return await self.service.enable_evolution()

    async def disable_evolution(self) -> dict:
        return await self.service.disable_evolution()

    async def evolution_cycle(self) -> dict:
        return await self.service.evolution_cycle()

    async def collect_periodic_reports(self, cadence: str) -> dict:
        return await self.service.collect_periodic_reports(cadence=cadence)
