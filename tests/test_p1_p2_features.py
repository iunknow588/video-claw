"""
Tests for P1 and P2 features.
"""
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from departments.CIO.services.scheduler.precise import (
    PreciseTriggerScanner,
    DistributedLock,
    MonitoredWorkflowEngine
)
from departments.CEO.services.orchestration.events import (
    WorkflowEvent,
    WorkflowEventType,
    EventDrivenEngine,
    WebhookTriggerSource,
    TriggerSourceRegistry
)
from departments.CEO.services.orchestration.context import (
    WorkflowContext,
    ContextAwareEngine
)
from departments.CIO.schemas.video import DomainWorkflowRequest


class TestPreciseTriggerScanner:
    """Tests for P1-A: Precise cron scheduling."""
    
    @pytest.fixture
    def mock_engine(self):
        engine = Mock()
        engine.run_domain_workflow = AsyncMock(return_value={
            'status': 'completed'
        })
        return engine
    
    @pytest.mark.asyncio
    async def test_precise_cron_job_creation(self, mock_engine):
        """Test that cron jobs are created with exact cron expressions."""
        scanner = PreciseTriggerScanner(
            workflow_engine=mock_engine,
            redis_host="localhost"
        )
        
        trigger = Mock()
        trigger.uuid = "trigger-1"
        trigger.cron = "0 3 * * *"  # Daily at 3 AM
        trigger.enabled = True
        trigger.domain = "technology"
        trigger.platform = "douyin"
        trigger.input_params = {}
        
        # Mock scheduler methods
        scanner.scheduler = Mock()
        scanner.scheduler.add_job = Mock()
        scanner.scheduler.get_job = Mock(return_value=None)
        
        await scanner.add_trigger(trigger)
        
        # Verify cron job was created with correct expression
        call_args = scanner.scheduler.add_job.call_args
        assert call_args[1]['trigger'] is not None
        assert call_args[1]['id'] == "trigger_trigger-1"
        
    @pytest.mark.asyncio
    async def test_job_persistence(self, mock_engine):
        """Test that jobs persist with Redis job store."""
        scanner = PreciseTriggerScanner(
            workflow_engine=mock_engine,
            redis_host="localhost"
        )
        
        # Verify Redis job store is configured
        assert 'default' in scanner.jobstores
        assert scanner.jobstores['default'] is not None


class TestDistributedLock:
    """Tests for P1-C: Distributed locking."""
    
    @pytest.fixture
    def mock_redis(self):
        redis = Mock()
        redis.set = AsyncMock(return_value=True)
        redis.delete = AsyncMock()
        redis.expire = AsyncMock()
        return redis
    
    @pytest.mark.asyncio
    async def test_lock_acquisition(self, mock_redis):
        """Test acquiring a distributed lock."""
        lock = DistributedLock(mock_redis)
        
        result = await lock.acquire("trigger:123", ttl_seconds=300)
        
        assert result is True
        mock_redis.set.assert_called_once_with(
            "trigger:123", "1", nx=True, ex=300
        )
        
    @pytest.mark.asyncio
    async def test_lock_release(self, mock_redis):
        """Test releasing a distributed lock."""
        lock = DistributedLock(mock_redis)
        
        await lock.release("trigger:123")
        
        mock_redis.delete.assert_called_once_with("trigger:123")
        
    @pytest.mark.asyncio
    async def test_lock_extend(self, mock_redis):
        """Test extending lock expiration."""
        lock = DistributedLock(mock_redis)
        
        await lock.extend("trigger:123", additional_ttl=600)
        
        mock_redis.expire.assert_called_once_with("trigger:123", 600)


class TestMonitoredWorkflowEngine:
    """Tests for P1-D: Monitoring and metrics."""
    
    @pytest.fixture
    def mock_base_engine(self):
        engine = Mock()
        engine.run_domain_workflow = AsyncMock(return_value={
            'status': 'completed'
        })
        return engine
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, mock_base_engine):
        """Test that metrics are collected during execution."""
        monitored = MonitoredWorkflowEngine(mock_base_engine)
        
        # Mock metrics
        monitored._metrics_enabled = True
        monitored.trigger_fired_total = Mock()
        monitored.trigger_execution_duration = Mock()
        monitored.active_runs_gauge = Mock()
        
        request = DomainWorkflowRequest(domain="technology", platform="douyin")
        result = await monitored.run_domain_workflow(
            request,
            trigger_id="trigger-1"
        )
        
        # Verify metrics were recorded
        monitored.active_runs_gauge.labels.assert_called()
        monitored.trigger_fired_total.labels.assert_called_with(
            trigger_id="trigger-1",
            status='success'
        )
        
    @pytest.mark.asyncio
    async def test_failure_metrics(self, mock_base_engine):
        """Test that failure metrics are recorded."""
        mock_base_engine.run_domain_workflow = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        monitored = MonitoredWorkflowEngine(mock_base_engine)
        monitored._metrics_enabled = True
        monitored.trigger_fired_total = Mock()
        monitored.active_runs_gauge = Mock()
        
        request = DomainWorkflowRequest(domain="technology", platform="douyin")
        with pytest.raises(Exception):
            await monitored.run_domain_workflow(
                request,
                trigger_id="trigger-1"
            )
            
        # Verify failure metric was recorded
        monitored.trigger_fired_total.labels.assert_called_with(
            trigger_id="trigger-1",
            status='failed'
        )


class TestEventDrivenEngine:
    """Tests for P2-A: Event-driven workflow."""
    
    @pytest.fixture
    def mock_workflow_engine(self):
        engine = Mock()
        engine.run_domain_workflow = AsyncMock(return_value={
            'status': 'completed'
        })
        return engine
    
    @pytest.fixture
    def mock_trigger_service(self):
        service = Mock()
        return service
    
    @pytest.mark.asyncio
    async def test_event_processing(self, mock_workflow_engine, mock_trigger_service):
        """Test processing of workflow events."""
        event_engine = EventDrivenEngine(
            workflow_engine=mock_workflow_engine,
            trigger_service=mock_trigger_service
        )
        
        # Create test event
        event = WorkflowEvent(
            event_type=WorkflowEventType.WEBHOOK,
            payload={"action": "publish"},
            source="webhook:test"
        )
        
        # Mock finding triggers
        mock_trigger = Mock()
        mock_trigger.uuid = "trigger-1"
        mock_trigger.domain = "technology"
        mock_trigger.platform = "douyin"
        mock_trigger.input_params = {"default": "value"}
        mock_trigger.enabled = True
        
        event_engine._find_triggers_for_event = AsyncMock(
            return_value=[mock_trigger]
        )
        
        await event_engine._handle_event(event)
        
        call = mock_workflow_engine.run_domain_workflow.call_args
        request = call.args[0]
        assert request.domain == "technology"
        assert request.platform == "douyin"
        assert request.publish_goal is None
        assert call.kwargs["trigger_id"] == "trigger-1"
        
    @pytest.mark.asyncio
    async def test_event_payload_merge(self, mock_workflow_engine, mock_trigger_service):
        """Test that event payload merges with trigger defaults."""
        event_engine = EventDrivenEngine(
            workflow_engine=mock_workflow_engine,
            trigger_service=mock_trigger_service
        )
        
        # Event payload should override defaults
        defaults = {"key1": "default", "key2": "default"}
        event_payload = {"key2": "overridden", "key3": "new"}
        
        merged = event_engine._merge_payload(defaults, event_payload)
        
        assert merged == {
            "key1": "default",
            "key2": "overridden",
            "key3": "new"
        }


class TestTriggerSourceRegistry:
    """Tests for P2-B: Plugin system."""
    
    def test_source_registration(self):
        """Test that trigger sources can be registered."""
        registry = TriggerSourceRegistry()
        
        # Clear existing
        registry._sources = {}
        
        # Register webhook source
        registry.register(WebhookTriggerSource)
        
        assert "webhook" in registry.list_sources()
        
    def test_source_creation(self):
        """Test creating trigger source instances."""
        registry = TriggerSourceRegistry()
        registry._sources = {}
        registry.register(WebhookTriggerSource)
        
        source = registry.create("webhook", host="0.0.0.0", port=8080)
        
        assert isinstance(source, WebhookTriggerSource)
        assert source.host == "0.0.0.0"
        assert source.port == 8080


class TestWorkflowContext:
    """Tests for P2-D: Dynamic context."""
    
    def test_context_set_get(self):
        """Test basic context variable storage."""
        ctx = WorkflowContext(run_id="run-1")
        
        ctx.set("budget", 1000, scope="CFO")
        ctx.set("queries", ["AI"], scope="Research")
        
        assert ctx.get("budget", scope="CFO") == 1000
        assert ctx.get("queries", scope="Research") == ["AI"]
        
    def test_template_resolution(self):
        """Test template string resolution."""
        ctx = WorkflowContext(run_id="run-1")
        
        ctx.set("budget", 1000, scope="CFO")
        ctx.set("queries", ["AI", "ML"], scope="Research")
        
        template = "Budget: {{CFO.budget}}, Queries: {{Research.queries}}"
        resolved = ctx.resolve(template)
        
        assert resolved == "Budget: 1000, Queries: ['AI', 'ML']"
        
    def test_template_with_default(self):
        """Test template with default value."""
        ctx = WorkflowContext(run_id="run-1")
        
        template = "Value: {{Missing.value:default}}"
        resolved = ctx.resolve(template)
        
        assert resolved == "Value: default"
        
    def test_context_snapshot(self):
        """Test context snapshots for audit."""
        ctx = WorkflowContext(run_id="run-1")
        
        ctx.set("budget", 1000, scope="CFO")
        ctx.snapshot("CFO")
        
        ctx.set("queries", ["AI"], scope="Research")
        ctx.snapshot("Research")
        
        snapshots = ctx.get_snapshots()
        
        assert len(snapshots) == 2
        assert snapshots[0]['stage'] == "CFO"
        assert snapshots[1]['stage'] == "Research"
        
    def test_context_dict_roundtrip(self):
        """Test context serialization/deserialization."""
        ctx = WorkflowContext(run_id="run-1", trigger_id="trigger-1")
        ctx.set("key", "value")
        ctx.snapshot("Test")
        
        data = ctx.to_dict()
        restored = WorkflowContext.from_dict(data)
        
        assert restored.run_id == "run-1"
        assert restored.trigger_id == "trigger-1"
        assert restored.get("key") == "value"


class TestContextAwareEngine:
    """Tests for context-aware workflow execution."""
    
    @pytest.fixture
    def mock_base_engine(self):
        engine = Mock()
        engine.run_domain_workflow = AsyncMock(return_value={
            'status': 'completed'
        })
        return engine
    
    @pytest.mark.asyncio
    async def test_context_creation(self, mock_base_engine):
        """Test that context is created with initial values."""
        engine = ContextAwareEngine(mock_base_engine)
        request = DomainWorkflowRequest(
            domain="technology",
            platform="douyin",
            audience="young-professionals",
        )
        
        result = await engine.run_domain_workflow(
            request,
            trigger_id="trigger-1",
            event_context={"event_type": "webhook"}
        )
        
        # Verify result contains context snapshots
        assert 'context_snapshots' in result
        assert result['context_snapshots'][0]['stage'] == "bootstrap"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
