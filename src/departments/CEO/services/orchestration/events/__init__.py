"""
Event-driven workflow engine.
P2-A implementation.
"""
import asyncio
from datetime import UTC, datetime
from enum import Enum, auto
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
import logging
import uuid

from sqlalchemy import and_, select

from departments.CIO.db.session import database_runtime
from departments.CIO.models.workflow import WorkflowTrigger
from departments.CIO.schemas.video import DomainWorkflowRequest

logger = logging.getLogger(__name__)


class WorkflowEventType(Enum):
    """Supported workflow event types."""
    SCHEDULED = "scheduled"          # 定时触发
    WEBHOOK = "webhook"              # 外部 webhook
    MANUAL = "manual"                # 手动触发
    HOTSPOT_DETECTED = "hotspot"     # 热点发现
    USER_ACTION = "user_action"      # 用户行为
    SYSTEM_ALERT = "system_alert"    # 系统告警
    

@dataclass
class WorkflowEvent:
    """Workflow event with context."""
    event_type: WorkflowEventType
    payload: Dict[str, Any]
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'payload': self.payload,
            'source': self.source,
            'timestamp': self.timestamp.isoformat()
        }


class EventDrivenEngine:
    """
    Event-driven workflow engine supporting multiple trigger sources.
    
    Features:
    - Multiple event type support
    - Event payload merging with trigger defaults
    - Async event processing
    - Event history tracking
    """
    
    def __init__(
        self,
        workflow_engine,
        trigger_service,
        event_handlers: Optional[Dict[WorkflowEventType, List[Callable]]] = None
    ):
        self.workflow_engine = workflow_engine
        self.trigger_service = trigger_service
        self.event_handlers = event_handlers or {}
        self._event_queue = asyncio.Queue()
        self._processing = False
        
    async def start(self):
        """Start event processing loop."""
        self._processing = True
        asyncio.create_task(self._process_events())
        logger.info("EventDrivenEngine started")
        
    async def stop(self):
        """Stop event processing."""
        self._processing = False
        logger.info("EventDrivenEngine stopped")
        
    async def emit_event(self, event: WorkflowEvent):
        """
        Emit an event to the processing queue.
        
        Args:
            event: WorkflowEvent to process
        """
        await self._event_queue.put(event)
        logger.debug(f"Event {event.event_id} queued: {event.event_type.value}")
        
    async def handle_webhook(self, trigger_id: str, payload: Dict[str, Any]):
        """
        Handle incoming webhook.
        
        Args:
            trigger_id: Trigger ID from webhook URL
            payload: Webhook JSON payload
        """
        event = WorkflowEvent(
            event_type=WorkflowEventType.WEBHOOK,
            payload=payload,
            source=f"webhook:{trigger_id}"
        )
        await self.emit_event(event)
        
    async def handle_hotspot_detected(self, hotspot_data: Dict[str, Any]):
        """
        Handle hotspot detection event.
        
        Args:
            hotspot_data: Hotspot detection result
        """
        event = WorkflowEvent(
            event_type=WorkflowEventType.HOTSPOT_DETECTED,
            payload=hotspot_data,
            source="hotspot_detector"
        )
        await self.emit_event(event)
        
    async def _process_events(self):
        """Main event processing loop."""
        while self._processing:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                await self._handle_event(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event processing error: {e}")
                
    async def _handle_event(self, event: WorkflowEvent):
        """
        Handle a single event.
        
        1. Find triggers matching the event type
        2. Merge event payload with trigger defaults
        3. Execute workflow
        """
        logger.info(f"Processing event {event.event_id}: {event.event_type.value}")
        
        # Find triggers for this event type
        triggers = await self._find_triggers_for_event(event)
        
        if not triggers:
            logger.debug(f"No triggers found for event type {event.event_type.value}")
            return
            
        # Execute workflow for each matching trigger
        for trigger in triggers:
            try:
                # Merge event payload with trigger defaults
                merged_input = self._merge_payload(
                    trigger.input_params or {},
                    event.payload
                )
                
                # Add event context
                event_context = {
                    'event_type': event.event_type.value,
                    'event_source': event.source,
                    'event_timestamp': event.timestamp.isoformat(),
                    'event_id': event.event_id
                }
                
                request = DomainWorkflowRequest(
                    domain=trigger.domain,
                    platform=trigger.platform,
                    hotspot_count=merged_input.get("hotspot_count", 12),
                    top_n=merged_input.get("top_n", 3),
                    content_type=merged_input.get("content_type", "knowledge"),
                    style=merged_input.get("style", "clean"),
                    video_style=merged_input.get("video_style", "realistic"),
                    duration=merged_input.get("duration", 30),
                    audience=merged_input.get("audience"),
                    publish_goal=merged_input.get("publish_goal"),
                    auto_approve_script=merged_input.get("auto_approve_script", False),
                    auto_generate_video=merged_input.get("auto_generate_video", False),
                )

                result = await self.workflow_engine.run_domain_workflow(
                    request,
                    trigger_id=trigger.uuid,
                )
                
                logger.info(
                    f"Event {event.event_id} processed by trigger {trigger.uuid}: "
                    f"{result.get('status')}"
                )
                
            except Exception as e:
                logger.error(
                    f"Event {event.event_id} failed for trigger {trigger.uuid}: {e}"
                )
                
    async def _find_triggers_for_event(self, event: WorkflowEvent) -> List[Any]:
        """
        Find triggers that should respond to this event.
        
        For now, simple matching by event_type in trigger config.
        Future: more sophisticated matching with filters.
        """
        async with database_runtime.session_factory()() as session:
            # Find triggers that listen to this event type
            query = select(WorkflowTrigger).where(
                and_(
                    WorkflowTrigger.enabled.is_(True),
                    WorkflowTrigger.event_types.contains([event.event_type.value])
                )
            )
            
            result = await session.execute(query)
            return result.scalars().all()
            
    def _merge_payload(self, defaults: Dict[str, Any], event_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge event payload with trigger defaults.
        
        Event payload takes precedence over defaults.
        """
        merged = defaults.copy()
        merged.update(event_payload)
        return merged
        
    def register_handler(self, event_type: WorkflowEventType, handler: Callable[[WorkflowEvent], Awaitable[None]]):
        """
        Register a custom event handler.
        
        Args:
            event_type: Event type to handle
            handler: Async handler function
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)


# ============= Trigger Source Plugin System (P2-B) =============

from abc import ABC, abstractmethod

class TriggerSource(ABC):
    """Base class for trigger source plugins."""
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """Unique source type identifier."""
        pass
        
    @abstractmethod
    async def start(self, callback: Callable[[WorkflowEvent], Awaitable[None]]):
        """
        Start the trigger source.
        
        Args:
            callback: Function to call when event occurs
        """
        pass
        
    @abstractmethod
    async def stop(self):
        """Stop the trigger source."""
        pass
        
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if source is healthy."""
        pass


class WebhookTriggerSource(TriggerSource):
    """HTTP webhook trigger source."""
    
    source_type = "webhook"
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self._app = None
        self._runner = None
        self._callback = None
        
    async def start(self, callback):
        from aiohttp import web
        
        self._callback = callback
        self._app = web.Application()
        self._app.router.add_post('/webhook/{trigger_id}', self._handle_webhook)
        
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        
        logger.info(f"Webhook server started on {self.host}:{self.port}")
        
    async def stop(self):
        if self._runner:
            await self._runner.cleanup()
            
    async def health_check(self) -> bool:
        return self._runner is not None
        
    async def _handle_webhook(self, request):
        from aiohttp import web
        
        trigger_id = request.match_info['trigger_id']
        payload = await request.json()
        
        event = WorkflowEvent(
            event_type=WorkflowEventType.WEBHOOK,
            payload=payload,
            source=f"webhook:{trigger_id}"
        )
        
        await self._callback(event)
        return web.Response(status=200, text="OK")


class TriggerSourceRegistry:
    """Registry for trigger source plugins."""
    
    _sources: Dict[str, type] = {}
    
    @classmethod
    def register(cls, source_class: type):
        """Register a trigger source plugin."""
        cls._sources[source_class.source_type] = source_class
        logger.info(f"Registered trigger source: {source_class.source_type}")
        
    @classmethod
    def create(cls, source_type: str, **config) -> TriggerSource:
        """Create a trigger source instance."""
        if source_type not in cls._sources:
            raise ValueError(f"Unknown trigger source: {source_type}")
        return cls._sources[source_type](**config)
        
    @classmethod
    def list_sources(cls) -> List[str]:
        """List registered source types."""
        return list(cls._sources.keys())


# Register built-in sources
TriggerSourceRegistry.register(WebhookTriggerSource)
