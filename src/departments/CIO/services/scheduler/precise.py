"""
Precise cron scheduler with Redis job store support.
P1-A + P1-B implementation.
"""
import asyncio
import uuid
from contextlib import nullcontext
from datetime import UTC, datetime
from typing import Optional, Dict, Any, Callable, Awaitable
import logging

from sqlalchemy import select

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.jobstores.redis import RedisJobStore
    from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
except ModuleNotFoundError:  # pragma: no cover - optional runtime dependency
    class RedisJobStore:  # type: ignore[override]
        def __init__(self, **kwargs):
            self.config = kwargs

    class _FallbackCronTrigger:
        def __init__(self, expr: str):
            self.expr = expr

        @classmethod
        def from_crontab(cls, expr: str):
            return cls(expr)

    class _FallbackScheduler:
        def __init__(self, jobstores=None):
            self.jobstores = jobstores or {}
            self._jobs: dict[str, dict[str, Any]] = {}
            self._listeners: list[tuple[Callable[..., Any], int]] = []

        def add_listener(self, callback, mask):
            self._listeners.append((callback, mask))

        def start(self):
            return None

        def shutdown(self, wait=True):
            return None

        def add_job(self, **kwargs):
            self._jobs[kwargs["id"]] = kwargs
            return kwargs

        def get_job(self, job_id):
            return self._jobs.get(job_id)

        def remove_job(self, job_id):
            self._jobs.pop(job_id, None)

        def pause_job(self, job_id):
            return None

        def resume_job(self, job_id):
            return None

    AsyncIOScheduler = _FallbackScheduler  # type: ignore[assignment]
    CronTrigger = _FallbackCronTrigger  # type: ignore[assignment]
    EVENT_JOB_EXECUTED = 1
    EVENT_JOB_ERROR = 2

from departments.CIO.db.session import database_runtime
from departments.CIO.models.workflow import WorkflowTrigger
from departments.CIO.schemas.video import DomainWorkflowRequest

logger = logging.getLogger(__name__)


class PreciseTriggerScanner:
    """
    Production-grade trigger scanner with precise cron scheduling.
    
    Features:
    - Per-trigger cron jobs (not polling)
    - Redis job store for distributed deployment
    - Job persistence across restarts
    - Event-driven execution callbacks
    """
    
    def __init__(
        self,
        workflow_engine,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        jobstore_key: str = "apscheduler"
    ):
        self.workflow_engine = workflow_engine
        
        # Configure Redis job store for distributed support
        self.jobstores = {
            'default': RedisJobStore(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                jobs_key=f'{jobstore_key}.jobs',
                run_times_key=f'{jobstore_key}.run_times'
            )
        }
        
        self.scheduler = AsyncIOScheduler(jobstores=self.jobstores)
        self._setup_event_listeners()
        
    def _setup_event_listeners(self):
        """Setup APScheduler event listeners for monitoring."""
        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        
    async def start(self):
        """Start the scheduler and load existing triggers."""
        logger.info("Starting PreciseTriggerScanner with Redis job store...")
        
        self.scheduler.start()
        
        # Load all enabled triggers from database
        await self._load_triggers()
        
        logger.info("PreciseTriggerScanner started")
        
    async def stop(self):
        """Stop the scheduler gracefully."""
        logger.info("Stopping PreciseTriggerScanner...")
        self.scheduler.shutdown(wait=True)
        logger.info("PreciseTriggerScanner stopped")
        
    async def add_trigger(self, trigger: WorkflowTrigger):
        """
        Add a trigger as a precise cron job.
        
        Args:
            trigger: WorkflowTrigger instance with cron expression
        """
        job_id = f"trigger_{trigger.uuid}"
        
        # Remove existing job if present
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            
        # Add new cron job
        self.scheduler.add_job(
            func=self._execute_trigger,
            trigger=CronTrigger.from_crontab(trigger.cron),
            id=job_id,
            replace_existing=True,
            args=[trigger.uuid],
            misfire_grace_time=3600,  # 1 hour grace period
            coalesce=True  # Coalesce missed jobs into one
        )
        
        logger.info(f"Added precise cron job for trigger {trigger.uuid}: {trigger.cron}")
        
    async def remove_trigger(self, trigger_id: str):
        """Remove a trigger's scheduled job."""
        job_id = f"trigger_{trigger_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job for trigger {trigger_id}")
            
    async def pause_trigger(self, trigger_id: str):
        """Pause a trigger's scheduled job."""
        job_id = f"trigger_{trigger_id}"
        self.scheduler.pause_job(job_id)
        
    async def resume_trigger(self, trigger_id: str):
        """Resume a trigger's scheduled job."""
        job_id = f"trigger_{trigger_id}"
        self.scheduler.resume_job(job_id)
        
    async def _load_triggers(self):
        """Load all enabled triggers from database."""
        async with database_runtime.session_factory()() as session:
            query = select(WorkflowTrigger).where(WorkflowTrigger.enabled == True)
            result = await session.execute(query)
            triggers = result.scalars().all()
            
            for trigger in triggers:
                await self.add_trigger(trigger)
                
            logger.info(f"Loaded {len(triggers)} triggers from database")
            
    async def _execute_trigger(self, trigger_id: str):
        """Execute workflow for a trigger (called by APScheduler)."""
        logger.info(f"Executing trigger {trigger_id}")
        
        # Fetch trigger from database
        async with database_runtime.session_factory()() as session:
            result = await session.execute(select(WorkflowTrigger).where(WorkflowTrigger.uuid == trigger_id))
            trigger = result.scalar_one_or_none()
            
            if not trigger or not trigger.enabled:
                logger.warning(f"Trigger {trigger_id} not found or disabled")
                return
                
            # Update last_fired_at
            trigger.last_fired_at = datetime.now(UTC)
            await session.commit()
            
        # Execute workflow
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
                trigger_id=trigger.uuid
            )
            logger.info(f"Trigger {trigger_id} completed: {result.get('status')}")
            
        except Exception as e:
            logger.error(f"Trigger {trigger_id} failed: {e}")
            # Don't re-raise - let APScheduler handle it
            
    def _on_job_executed(self, event):
        """Handle job execution events for monitoring."""
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        else:
            logger.debug(f"Job {event.job_id} executed successfully")


class DistributedLock:
    """
    Redis-based distributed lock for trigger execution.
    P1-C implementation.
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        
    async def acquire(self, lock_key: str, ttl_seconds: int = 300) -> bool:
        """
        Acquire a distributed lock.
        
        Args:
            lock_key: Unique lock identifier
            ttl_seconds: Lock expiration time
            
        Returns:
            True if lock acquired, False otherwise
        """
        # NX = only if Not eXists, EX = expiration in seconds
        result = await self.redis.set(lock_key, "1", nx=True, ex=ttl_seconds)
        return result is not None
        
    async def release(self, lock_key: str):
        """Release a distributed lock."""
        await self.redis.delete(lock_key)
        
    async def extend(self, lock_key: str, additional_ttl: int):
        """Extend lock expiration."""
        await self.redis.expire(lock_key, additional_ttl)


class MonitoredWorkflowEngine:
    """
    Workflow engine wrapper with Prometheus metrics.
    P1-D implementation.
    """

    _shared_metrics: dict[str, Any] | None = None
    
    def __init__(self, engine):
        self.engine = engine
        self._setup_metrics()
        
    def _setup_metrics(self):
        """Setup Prometheus metrics."""
        if self.__class__._shared_metrics is not None:
            metrics = self.__class__._shared_metrics
            self.trigger_fired_total = metrics["trigger_fired_total"]
            self.trigger_execution_duration = metrics["trigger_execution_duration"]
            self.active_runs_gauge = metrics["active_runs_gauge"]
            self._metrics_enabled = True
            return

        try:
            from prometheus_client import Counter, Histogram, Gauge
            
            self.trigger_fired_total = Counter(
                'trigger_fired_total',
                'Total triggers fired',
                ['trigger_id', 'status']
            )
            self.trigger_execution_duration = Histogram(
                'trigger_execution_duration_seconds',
                'Trigger execution time'
            )
            self.active_runs_gauge = Gauge(
                'active_workflow_runs',
                'Currently running workflows',
                ['trigger_id']
            )
            self.__class__._shared_metrics = {
                "trigger_fired_total": self.trigger_fired_total,
                "trigger_execution_duration": self.trigger_execution_duration,
                "active_runs_gauge": self.active_runs_gauge,
            }
            self._metrics_enabled = True
            
        except ImportError:
            logger.warning("prometheus_client not installed, metrics disabled")
            self._metrics_enabled = False

    def _build_timer_context(self):
        """Return a safe timer context manager for metrics and tests."""
        timer_factory = getattr(self.trigger_execution_duration, "time", None)
        if not callable(timer_factory):
            return nullcontext()
        timer = timer_factory()
        if hasattr(timer, "__enter__") and hasattr(timer, "__exit__"):
            return timer
        return nullcontext()
            
    async def run_domain_workflow(
        self,
        request: DomainWorkflowRequest,
        *,
        trigger_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ):
        """Execute workflow with metrics collection."""
        metric_trigger_id = trigger_id or "manual"
        
        if self._metrics_enabled:
            self.active_runs_gauge.labels(trigger_id=metric_trigger_id).inc()
            
        start_time = datetime.now(UTC)
        
        try:
            with self._build_timer_context():
                result = await self.engine.run_domain_workflow(
                    request,
                    trigger_id=trigger_id,
                    trace_id=trace_id,
                )
                
            if self._metrics_enabled:
                self.trigger_fired_total.labels(
                    trigger_id=metric_trigger_id,
                    status='success'
                ).inc()
                
            return result
            
        except Exception as e:
            if self._metrics_enabled:
                self.trigger_fired_total.labels(
                    trigger_id=metric_trigger_id,
                    status='failed'
                ).inc()
            raise
            
        finally:
            if self._metrics_enabled:
                self.active_runs_gauge.labels(trigger_id=metric_trigger_id).dec()
                
            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.info(f"Trigger {metric_trigger_id} execution duration: {duration}s")
