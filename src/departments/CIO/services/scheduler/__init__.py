"""
Trigger scheduling and CRUD services.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import and_, or_, select

from departments.CIO.db.session import database_runtime
from departments.CIO.models.workflow import WorkflowRun, WorkflowTrigger

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
except ModuleNotFoundError:  # pragma: no cover - optional runtime dependency
    AsyncIOScheduler = None
    CronTrigger = None

from departments.CIO.schemas.video import DomainWorkflowRequest


class TriggerService:
    """CRUD service for workflow triggers."""

    async def create_trigger(
        self,
        *,
        name: str,
        cron: str,
        domain: str,
        platform: str,
        input_params: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> WorkflowTrigger:
        now = datetime.now(UTC)
        trigger = WorkflowTrigger(
            name=name,
            cron=cron,
            domain=domain,
            platform=platform,
            input_params=input_params or {},
            enabled=enabled,
            next_fire_at=self._calculate_next_fire(cron, now) if enabled else None,
        )
        async with database_runtime.session_factory()() as session:
            session.add(trigger)
            await session.commit()
            await session.refresh(trigger)
            return trigger

    async def list_triggers(
        self,
        *,
        enabled: bool | None = None,
        limit: int = 100,
    ) -> list[WorkflowTrigger]:
        async with database_runtime.session_factory()() as session:
            query = select(WorkflowTrigger).order_by(WorkflowTrigger.created_at.desc()).limit(limit)
            if enabled is not None:
                query = query.where(WorkflowTrigger.enabled == enabled)
            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_trigger(self, trigger_id: str) -> WorkflowTrigger | None:
        async with database_runtime.session_factory()() as session:
            query = select(WorkflowTrigger).where(WorkflowTrigger.uuid == trigger_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def update_trigger(self, trigger_id: str, **updates: Any) -> WorkflowTrigger | None:
        async with database_runtime.session_factory()() as session:
            result = await session.execute(select(WorkflowTrigger).where(WorkflowTrigger.uuid == trigger_id))
            trigger = result.scalar_one_or_none()
            if not trigger:
                return None

            for key, value in updates.items():
                setattr(trigger, key, value)

            if "cron" in updates or "enabled" in updates:
                if trigger.enabled:
                    trigger.next_fire_at = self._calculate_next_fire(trigger.cron, datetime.now(UTC))
                else:
                    trigger.next_fire_at = None

            trigger.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(trigger)
            return trigger

    async def delete_trigger(self, trigger_id: str) -> bool:
        async with database_runtime.session_factory()() as session:
            result = await session.execute(select(WorkflowTrigger).where(WorkflowTrigger.uuid == trigger_id))
            trigger = result.scalar_one_or_none()
            if not trigger:
                return False
            await session.delete(trigger)
            await session.commit()
            return True

    def _calculate_next_fire(self, cron_expr: str, from_time: datetime) -> datetime:
        if CronTrigger is None:
            return from_time + timedelta(minutes=1)
        trigger = CronTrigger.from_crontab(cron_expr, timezone=from_time.tzinfo)
        next_time = trigger.get_next_fire_time(None, from_time)
        return next_time or from_time + timedelta(days=1)


class TriggerScanner:
    """
    Minimal trigger scanner with cooldown and active-run deduplication.
    """

    def __init__(
        self,
        workflow_engine,
        cooldown_seconds: int = 60,
        check_interval_seconds: int = 30,
    ):
        self.workflow_engine = workflow_engine
        self.cooldown_seconds = cooldown_seconds
        self.check_interval_seconds = check_interval_seconds
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._shutdown_event = asyncio.Event()

    async def start(self):
        """Start the trigger scanner."""
        logger.info("Starting TriggerScanner...")
        if AsyncIOScheduler is None:
            raise RuntimeError("apscheduler is required to start TriggerScanner")

        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(
            self._scan_and_trigger,
            "interval",
            seconds=self.check_interval_seconds,
            id="trigger_scanner",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info("TriggerScanner started, checking every %ss", self.check_interval_seconds)

    async def stop(self):
        """Stop the trigger scanner gracefully."""
        logger.info("Stopping TriggerScanner...")
        self._shutdown_event.set()
        if self.scheduler:
            self.scheduler.shutdown(wait=True)
        logger.info("TriggerScanner stopped")

    async def _scan_and_trigger(self):
        """Scan due triggers and fire them."""
        if self._shutdown_event.is_set():
            return

        now = datetime.now(UTC)
        try:
            async with database_runtime.session_factory()() as session:
                query = (
                    select(WorkflowTrigger)
                    .where(
                        and_(
                            WorkflowTrigger.enabled.is_(True),
                            or_(
                                WorkflowTrigger.next_fire_at.is_(None),
                                WorkflowTrigger.next_fire_at <= now,
                            ),
                        )
                    )
                    .order_by(WorkflowTrigger.next_fire_at.asc(), WorkflowTrigger.created_at.asc())
                )
                result = await session.execute(query)
                triggers = list(result.scalars().all())

                for trigger in triggers:
                    await self._fire_trigger(trigger, session)

                if triggers:
                    await session.commit()
        except Exception as exc:
            logger.error("Trigger scan failed: %s", exc)

    async def _fire_trigger(self, trigger: WorkflowTrigger, session):
        """
        Fire a single trigger with cooldown and active-run dedupe.
        """
        now = datetime.now(UTC)
        trigger_key = trigger.uuid

        if trigger.last_fired_at:
            last_fired_at = trigger.last_fired_at
            if last_fired_at.tzinfo is None:
                last_fired_at = last_fired_at.replace(tzinfo=UTC)
            cooldown_end = last_fired_at + timedelta(seconds=self.cooldown_seconds)
            if now < cooldown_end:
                logger.debug("Trigger %s in cooldown until %s", trigger_key, cooldown_end)
                return

        duplicate_query = select(WorkflowRun).where(
            and_(
                WorkflowRun.trigger_id == trigger_key,
                WorkflowRun.status.in_(["pending", "running"]),
            )
        )
        duplicate_result = await session.execute(duplicate_query)
        existing_runs = list(duplicate_result.scalars().all())
        if existing_runs:
            logger.warning(
                "Trigger %s has %s active runs, skipping duplicate fire",
                trigger_key,
                len(existing_runs),
            )
            return

        logger.info("Firing trigger %s (%s)", trigger_key, trigger.name)
        trigger.last_fired_at = now
        trigger.next_fire_at = TriggerService()._calculate_next_fire(trigger.cron, now)
        asyncio.create_task(self._execute_workflow(trigger))

    async def _execute_workflow(self, trigger: WorkflowTrigger):
        """Execute workflow for a trigger."""
        trigger_key = trigger.uuid
        try:
            request = DomainWorkflowRequest(
                domain=trigger.domain,
                platform=trigger.platform,
                hotspot_count=(trigger.input_params or {}).get("hotspot_count", 12),
                top_n=(trigger.input_params or {}).get("top_n", 3),
                content_type=(trigger.input_params or {}).get("content_type", "knowledge"),
                style=(trigger.input_params or {}).get("style", "clean"),
                video_style=(trigger.input_params or {}).get("video_style", "realistic"),
                duration=(trigger.input_params or {}).get("duration", 30),
                audience=(trigger.input_params or {}).get("audience"),
                publish_goal=(trigger.input_params or {}).get("publish_goal"),
                auto_approve_script=(trigger.input_params or {}).get("auto_approve_script", False),
                auto_generate_video=(trigger.input_params or {}).get("auto_generate_video", False),
            )
            result = await self.workflow_engine.run_domain_workflow(
                request,
                trigger_id=trigger_key,
            )
            logger.info("Trigger %s workflow completed: %s", trigger_key, result.get("status"))
        except Exception as exc:
            logger.error("Trigger %s workflow failed: %s", trigger_key, exc)


__all__ = ["TriggerScanner", "TriggerService"]
