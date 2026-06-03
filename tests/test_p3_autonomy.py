"""
Tests for P3 autonomous features.
"""
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from departments.CEO.services.orchestration.autonomy import (
    IntelligentRetryPolicy,
    AutonomousRecovery,
    PredictiveScheduler,
    RetryDecision,
    FailureDiagnosis
)


class TestIntelligentRetryPolicy:
    """Tests for P3-A: Intelligent retry."""
    
    @pytest.fixture
    def policy(self):
        return IntelligentRetryPolicy()
    
    @pytest.fixture
    def policy_with_llm(self):
        llm = Mock()
        llm.complete = AsyncMock(return_value=json.dumps({
            'type': 'transient',
            'recoverable': True,
            'confidence': 0.9,
            'root_cause': 'Network timeout',
            'suggested_action': 'retry'
        }))
        return IntelligentRetryPolicy(llm_client=llm)
    
    def test_heuristic_transient_detection(self, policy):
        """Test heuristic detection of transient errors."""
        failure = {
            'error': 'Connection timeout',
            'traceback': 'requests.exceptions.Timeout'
        }
        
        diagnosis = policy._heuristic_analyze(failure)
        
        assert diagnosis.failure_type == 'transient'
        assert diagnosis.recoverable is True
        
    def test_heuristic_fundamental_detection(self, policy):
        """Test heuristic detection of fundamental errors."""
        failure = {
            'error': 'Invalid API key',
            'traceback': 'AuthenticationError'
        }
        
        diagnosis = policy._heuristic_analyze(failure)
        
        assert diagnosis.failure_type == 'fundamental'
        assert diagnosis.recoverable is False
        
    @pytest.mark.asyncio
    async def test_llm_analysis(self, policy_with_llm):
        """Test LLM-based failure analysis."""
        failure = {'error': 'Something failed'}
        
        diagnosis = await policy_with_llm.analyze_failure(failure)
        
        assert diagnosis.failure_type == 'transient'
        assert diagnosis.confidence == 0.9
        
    @pytest.mark.asyncio
    async def test_retry_decision_transient(self, policy):
        """Test retry decision for transient errors."""
        failure = {'error': 'timeout'}
        
        decision = await policy.determine_retry(failure)
        
        assert decision.retry_now is True
        assert decision.delay_seconds == 30
        
    @pytest.mark.asyncio
    async def test_retry_decision_fundamental(self, policy):
        """Test retry decision for fundamental errors."""
        failure = {'error': 'invalid_api_key'}
        
        decision = await policy.determine_retry(failure)
        
        assert decision.retry_now is False
        assert decision.alert_severity == 'critical'


class TestAutonomousRecovery:
    """Tests for P3-C: Autonomous recovery."""
    
    @pytest.fixture
    def recovery(self):
        policy = IntelligentRetryPolicy()
        engine = Mock()
        engine.run_domain_workflow = AsyncMock(return_value={
            'status': 'completed'
        })
        alert = Mock()
        alert.send_alert = AsyncMock()
        
        return AutonomousRecovery(policy, engine, alert)
    
    @pytest.mark.asyncio
    async def test_successful_recovery(self, recovery):
        """Test successful auto-recovery."""
        failure = {'error': 'timeout', 'domain': 'technology'}

        with patch("departments.CEO.services.orchestration.autonomy.asyncio.sleep", new=AsyncMock()):
            result = await recovery.handle_failure('run-1', failure)
        
        assert result['final_status'] == 'recovered'
        assert 'auto_retry_success' in result['actions_taken']
        
    @pytest.mark.asyncio
    async def test_failed_recovery_escalation(self, recovery):
        """Test escalation when recovery fails."""
        recovery.workflow_engine.run_domain_workflow = AsyncMock(
            side_effect=Exception("Still failing")
        )
        
        failure = {'error': 'timeout', 'domain': 'technology'}
        with patch("departments.CEO.services.orchestration.autonomy.asyncio.sleep", new=AsyncMock()):
            result = await recovery.handle_failure('run-1', failure)
        
        assert result['final_status'] == 'escalated'
        recovery.alert_service.send_alert.assert_called()
        
    @pytest.mark.asyncio
    async def test_non_recoverable_escalation(self, recovery):
        """Test escalation for non-recoverable failures."""
        failure = {'error': 'invalid_api_key'}
        
        result = await recovery.handle_failure('run-1', failure)
        
        assert result['final_status'] == 'escalated'
        
    def test_recovery_stats(self, recovery):
        """Test recovery statistics."""
        # Add some mock history
        recovery._recovery_history = [
            {'final_status': 'recovered'},
            {'final_status': 'recovered'},
            {'final_status': 'escalated'}
        ]
        
        stats = recovery.get_recovery_stats()
        
        assert stats['total_incidents'] == 3
        assert stats['auto_recovered'] == 2
        assert stats['escalated'] == 1
        assert stats['recovery_rate'] == pytest.approx(0.667, 0.01)


class TestPredictiveScheduler:
    """Tests for P3-B: Predictive scheduling."""
    
    @pytest.fixture
    def scheduler(self):
        history = Mock()
        return PredictiveScheduler(history)
    
    @pytest.mark.asyncio
    async def test_optimize_with_sufficient_history(self, scheduler):
        """Test optimization with enough history."""
        scheduler.history_service.get_execution_history = AsyncMock(return_value=[
            {'execution_hour': 3, 'status': 'completed', 'cron': '0 3 * * *'},
            {'execution_hour': 3, 'status': 'completed'},
            {'execution_hour': 3, 'status': 'completed'},
            {'execution_hour': 3, 'status': 'completed'},
            {'execution_hour': 3, 'status': 'completed'},
            {'execution_hour': 3, 'status': 'completed'},
            {'execution_hour': 3, 'status': 'completed'},
            {'execution_hour': 3, 'status': 'completed'},
            {'execution_hour': 3, 'status': 'completed'},
            {'execution_hour': 3, 'status': 'completed'},
            {'execution_hour': 3, 'status': 'completed'},
        ])
        
        result = await scheduler.optimize_schedule('trigger-1')
        
        assert result is not None
        assert '3' in result  # Should suggest hour 3
        
    @pytest.mark.asyncio
    async def test_skip_with_insufficient_history(self, scheduler):
        """Test skipping optimization with too little history."""
        scheduler.history_service.get_execution_history = AsyncMock(return_value=[
            {'execution_hour': 3, 'status': 'completed'}
        ])
        
        result = await scheduler.optimize_schedule('trigger-1')
        
        assert result is None
        
    def test_hourly_pattern_analysis(self, scheduler):
        """Test hourly success pattern analysis."""
        history = [
            {'execution_hour': 3, 'status': 'completed'},
            {'execution_hour': 3, 'status': 'completed'},
            {'execution_hour': 3, 'status': 'failed'},
            {'execution_hour': 4, 'status': 'completed'},
            {'execution_hour': 4, 'status': 'completed'},
        ]
        
        patterns = scheduler._analyze_hourly_patterns(history)
        
        assert patterns[3]['success_rate'] == pytest.approx(0.667, 0.01)
        assert patterns[4]['success_rate'] == 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
