"""
Autonomous workflow recovery and intelligent retry.
P3-A + P3-C implementation.
"""
import asyncio
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import UTC, datetime
import logging

from departments.CIO.schemas.video import DomainWorkflowRequest

logger = logging.getLogger(__name__)


@dataclass
class RetryDecision:
    """Decision for retry strategy."""
    retry_now: bool
    delay_seconds: int = 0
    param_adjustments: Dict[str, Any] = None
    alert_severity: Optional[str] = None  # warning | critical | info
    reason: str = ""


@dataclass
class FailureDiagnosis:
    """Diagnosis of workflow failure."""
    failure_type: str  # transient | content_quality | fundamental | unknown
    recoverable: bool
    confidence: float  # 0.0 - 1.0
    root_cause: str
    suggested_action: str
    context: Dict[str, Any]


class IntelligentRetryPolicy:
    """
    Intelligent retry policy using LLM-based failure analysis.
    
    P3-A: Analyzes failure context to determine optimal retry strategy.
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self._fallback_rules = self._build_fallback_rules()
        
    def _build_fallback_rules(self) -> List[Dict]:
        """Build heuristic fallback rules when LLM is unavailable."""
        return [
            {
                'pattern': ['timeout', 'connection', 'network', '503', '502'],
                'type': 'transient',
                'retry': True,
                'delay': 30,
                'max_retries': 3
            },
            {
                'pattern': ['rate_limit', '429', 'too many requests'],
                'type': 'transient',
                'retry': True,
                'delay': 60,
                'max_retries': 5
            },
            {
                'pattern': ['content_policy', 'safety', 'moderation'],
                'type': 'content_quality',
                'retry': True,
                'delay': 0,
                'param_adjustments': {'temperature': 0.5, 'safer_prompt': True}
            },
            {
                'pattern': ['invalid_api_key', 'authentication', 'permission'],
                'type': 'fundamental',
                'retry': False,
                'alert': 'critical'
            },
            {
                'pattern': ['budget_exceeded', 'quota', 'limit'],
                'type': 'fundamental',
                'retry': False,
                'alert': 'warning'
            }
        ]
        
    async def analyze_failure(self, failure_context: Dict[str, Any]) -> FailureDiagnosis:
        """
        Analyze failure context to determine type and recoverability.
        
        Args:
            failure_context: Contains error, traceback, stage, artifacts
            
        Returns:
            FailureDiagnosis with type and suggested action
        """
        # Try LLM analysis first
        if self.llm_client:
            try:
                return await self._llm_analyze(failure_context)
            except Exception as e:
                logger.warning(f"LLM analysis failed, using fallback: {e}")
                
        # Fallback to heuristic rules
        return self._heuristic_analyze(failure_context)
        
    async def _llm_analyze(self, failure_context: Dict[str, Any]) -> FailureDiagnosis:
        """Use LLM to analyze failure."""
        prompt = self._build_analysis_prompt(failure_context)
        
        response = await self.llm_client.complete(prompt)
        analysis = json.loads(response)
        
        return FailureDiagnosis(
            failure_type=analysis['type'],
            recoverable=analysis['recoverable'],
            confidence=analysis['confidence'],
            root_cause=analysis['root_cause'],
            suggested_action=analysis['suggested_action'],
            context=failure_context
        )
        
    def _heuristic_analyze(self, failure_context: Dict[str, Any]) -> FailureDiagnosis:
        """Heuristic analysis based on error patterns."""
        error_str = json.dumps(failure_context).lower()
        
        for rule in self._fallback_rules:
            if any(pattern in error_str for pattern in rule['pattern']):
                return FailureDiagnosis(
                    failure_type=rule['type'],
                    recoverable=rule['retry'],
                    confidence=0.7,
                    root_cause=f"Matched pattern: {rule['pattern']}",
                    suggested_action="retry" if rule['retry'] else "escalate",
                    context=failure_context
                )
                
        return FailureDiagnosis(
            failure_type='unknown',
            recoverable=False,
            confidence=0.3,
            root_cause='No matching pattern found',
            suggested_action='escalate',
            context=failure_context
        )
        
    def _build_analysis_prompt(self, failure_context: Dict[str, Any]) -> str:
        """Build prompt for LLM failure analysis."""
        return f"""Analyze this workflow failure and classify it:

Error: {failure_context.get('error', 'Unknown')}
Stage: {failure_context.get('failed_stage', 'Unknown')}
Traceback: {failure_context.get('traceback', 'N/A')}

Respond in JSON format:
{{
    "type": "transient|content_quality|fundamental|unknown",
    "recoverable": true|false,
    "confidence": 0.0-1.0,
    "root_cause": "explanation",
    "suggested_action": "retry|escalate|skip"
}}
"""
        
    async def determine_retry(self, failure_context: Dict[str, Any]) -> RetryDecision:
        """
        Determine retry strategy based on failure analysis.
        
        Args:
            failure_context: Failure context
            
        Returns:
            RetryDecision with strategy
        """
        diagnosis = await self.analyze_failure(failure_context)
        
        if diagnosis.failure_type == 'transient':
            return RetryDecision(
                retry_now=True,
                delay_seconds=30,
                reason=f"Transient error: {diagnosis.root_cause}"
            )
            
        elif diagnosis.failure_type == 'content_quality':
            return RetryDecision(
                retry_now=True,
                delay_seconds=0,
                param_adjustments={
                    'temperature': 0.8,
                    'max_tokens': 2000,
                    'prompt_version': 'v2_safe'
                },
                reason=f"Content quality issue: {diagnosis.root_cause}"
            )
            
        elif diagnosis.failure_type == 'fundamental':
            return RetryDecision(
                retry_now=False,
                alert_severity='critical',
                reason=f"Fundamental error: {diagnosis.root_cause}"
            )
            
        else:
            return RetryDecision(
                retry_now=False,
                alert_severity='warning',
                reason=f"Unknown error: {diagnosis.root_cause}"
            )


class AutonomousRecovery:
    """
    Autonomous failure detection and recovery system.
    
    P3-C: Detects failures, attempts auto-recovery, escalates if needed.
    """
    
    def __init__(
        self,
        retry_policy: IntelligentRetryPolicy,
        workflow_engine,
        alert_service=None
    ):
        self.retry_policy = retry_policy
        self.workflow_engine = workflow_engine
        self.alert_service = alert_service
        self._recovery_history: List[Dict] = []
        
    async def handle_failure(self, run_id: str, failure: Dict[str, Any]):
        """
        Handle workflow failure with autonomous recovery.
        
        Steps:
        1. Diagnose failure
        2. Attempt auto-recovery if possible
        3. Escalate to human if needed
        """
        logger.info(f"Handling failure for run {run_id}")
        
        # Step 1: Diagnose
        diagnosis = await self.retry_policy.analyze_failure(failure)
        
        recovery_record = {
            'run_id': run_id,
            'timestamp': datetime.now(UTC).isoformat(),
            'diagnosis': diagnosis,
            'actions_taken': [],
            'final_status': 'pending'
        }
        
        # Step 2: Attempt recovery
        if diagnosis.recoverable:
            retry_decision = await self.retry_policy.determine_retry(failure)
            
            if retry_decision.retry_now:
                success = await self._attempt_recovery(
                    run_id, failure, retry_decision
                )
                
                if success:
                    recovery_record['actions_taken'].append('auto_retry_success')
                    recovery_record['final_status'] = 'recovered'
                else:
                    recovery_record['actions_taken'].append('auto_retry_failed')
                    recovery_record['final_status'] = 'escalated'
                    await self._escalate_to_human(run_id, failure, diagnosis)
            else:
                recovery_record['actions_taken'].append('retry_not_advised')
                recovery_record['final_status'] = 'escalated'
                await self._escalate_to_human(run_id, failure, diagnosis)
        else:
            recovery_record['actions_taken'].append('not_recoverable')
            recovery_record['final_status'] = 'escalated'
            await self._escalate_to_human(run_id, failure, diagnosis)
            
        self._recovery_history.append(recovery_record)
        return recovery_record
        
    async def _attempt_recovery(
        self,
        run_id: str,
        failure: Dict[str, Any],
        decision: RetryDecision
    ) -> bool:
        """Attempt to recover by retrying with adjusted parameters."""
        try:
            # Wait before retry if specified
            if decision.delay_seconds > 0:
                await asyncio.sleep(decision.delay_seconds)
                
            # Build recovery context
            recovery_context = {
                'original_run_id': run_id,
                'recovery_attempt': True,
                'param_adjustments': decision.param_adjustments or {}
            }
            
            # Retry workflow
            input_params = failure.get('input_params', {}) or {}
            request = DomainWorkflowRequest(
                domain=failure.get('domain', 'unknown'),
                platform=failure.get('platform', 'unknown'),
                hotspot_count=input_params.get("hotspot_count", 12),
                top_n=input_params.get("top_n", 3),
                content_type=input_params.get("content_type", "knowledge"),
                style=input_params.get("style", "clean"),
                video_style=input_params.get("video_style", "realistic"),
                duration=input_params.get("duration", 30),
                audience=input_params.get("audience"),
                publish_goal=input_params.get("publish_goal"),
                auto_approve_script=input_params.get("auto_approve_script", False),
                auto_generate_video=input_params.get("auto_generate_video", False),
            )
            result = await self.workflow_engine.run_domain_workflow(request)
            
            return result.get('status') == 'completed'
            
        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
            return False
            
    async def _escalate_to_human(
        self,
        run_id: str,
        failure: Dict[str, Any],
        diagnosis: FailureDiagnosis
    ):
        """Escalate to human operators."""
        alert = {
            'severity': 'critical' if diagnosis.failure_type == 'fundamental' else 'warning',
            'run_id': run_id,
            'failure_type': diagnosis.failure_type,
            'root_cause': diagnosis.root_cause,
            'suggested_action': diagnosis.suggested_action,
            'context': failure
        }
        
        if self.alert_service:
            await self.alert_service.send_alert(alert)
        else:
            logger.warning(f"ALERT: {json.dumps(alert, indent=2)}")
            
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        total = len(self._recovery_history)
        recovered = sum(1 for r in self._recovery_history if r['final_status'] == 'recovered')
        escalated = sum(1 for r in self._recovery_history if r['final_status'] == 'escalated')
        
        return {
            'total_incidents': total,
            'auto_recovered': recovered,
            'escalated': escalated,
            'recovery_rate': recovered / total if total > 0 else 0,
            'by_type': self._group_by_failure_type()
        }
        
    def _group_by_failure_type(self) -> Dict[str, int]:
        """Group incidents by failure type."""
        from collections import Counter
        types = []
        for record in self._recovery_history:
            diagnosis = record.get("diagnosis")
            failure_type = getattr(diagnosis, "failure_type", None) or "unknown"
            types.append(failure_type)
        return dict(Counter(types))


class PredictiveScheduler:
    """
    Predictive scheduling based on historical execution data.
    
    P3-B: Optimizes trigger timing based on past performance.
    """
    
    def __init__(self, history_service):
        self.history_service = history_service
        
    async def optimize_schedule(self, trigger_id: str) -> Optional[str]:
        """
        Analyze history and suggest optimal cron expression.
        
        Args:
            trigger_id: Trigger to optimize
            
        Returns:
            Suggested cron expression or None
        """
        history = await self.history_service.get_execution_history(
            trigger_id,
            days=30
        )
        
        if len(history) < 10:
            logger.info(f"Insufficient history for {trigger_id}, skipping optimization")
            return None
            
        # Simple heuristic: find hour with best success rate
        hourly_stats = self._analyze_hourly_patterns(history)
        best_hour = max(hourly_stats, key=lambda h: hourly_stats[h]['success_rate'])
        
        current_cron = history[0].get('cron', '0 3 * * *')
        
        # Suggest new cron if significantly better
        if hourly_stats[best_hour]['success_rate'] > 0.9:
            new_cron = f"0 {best_hour} * * *"
            logger.info(f"Suggested cron for {trigger_id}: {new_cron} "
                       f"(success rate: {hourly_stats[best_hour]['success_rate']:.2f})")
            return new_cron
            
        return None
        
    def _analyze_hourly_patterns(self, history: List[Dict]) -> Dict[int, Dict]:
        """Analyze success patterns by hour."""
        from collections import defaultdict
        
        hourly = defaultdict(lambda: {'total': 0, 'success': 0})
        
        for record in history:
            hour = record.get('execution_hour', 0)
            hourly[hour]['total'] += 1
            if record.get('status') == 'completed':
                hourly[hour]['success'] += 1
                
        return {
            hour: {
                'total': stats['total'],
                'success': stats['success'],
                'success_rate': stats['success'] / stats['total'] if stats['total'] > 0 else 0
            }
            for hour, stats in hourly.items()
        }
