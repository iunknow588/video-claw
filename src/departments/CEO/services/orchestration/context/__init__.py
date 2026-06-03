"""
Dynamic context management for workflow execution.
P2-D implementation.
"""
import re
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
import logging

from departments.CIO.schemas.video import DomainWorkflowRequest

logger = logging.getLogger(__name__)


@dataclass
class ContextVariable:
    """Context variable with metadata."""
    value: Any
    scope: str = "global"  # global | stage | run
    mutable: bool = True
    description: str = ""


class WorkflowContext:
    """
    Dynamic context manager for workflow execution.
    
    Features:
    - Scoped variable storage (global, stage, run)
    - Template resolution with {{scope.key}} syntax
    - Variable reference tracking
    - Immutable snapshots for audit
    """
    
    def __init__(self, run_id: str, trigger_id: Optional[str] = None):
        self.run_id = run_id
        self.trigger_id = trigger_id
        self._variables: Dict[str, ContextVariable] = {}
        self._snapshots: list = []
        
    def set(
        self,
        key: str,
        value: Any,
        scope: str = "global",
        description: str = ""
    ):
        """
        Set a context variable.
        
        Args:
            key: Variable name
            value: Variable value
            scope: Variable scope (global, stage, run)
            description: Optional description
        """
        full_key = f"{scope}:{key}"
        self._variables[full_key] = ContextVariable(
            value=value,
            scope=scope,
            description=description
        )
        logger.debug(f"Context set: {full_key} = {value}")
        
    def get(self, key: str, scope: str = "global", default: Any = None) -> Any:
        """
        Get a context variable.
        
        Args:
            key: Variable name
            scope: Variable scope
            default: Default value if not found
            
        Returns:
            Variable value or default
        """
        full_key = f"{scope}:{key}"
        var = self._variables.get(full_key)
        
        if var is None:
            return default
            
        # Resolve template references
        if isinstance(var.value, str):
            return self._resolve_template(var.value)
            
        return var.value
        
    def resolve(self, template: str) -> str:
        """
        Resolve a template string with context variables.
        
        Supports:
        - {{key}} -> global scope
        - {{scope.key}} -> specific scope
        - {{key:default}} -> with default value
        
        Args:
            template: Template string
            
        Returns:
            Resolved string
        """
        return self._resolve_template(template)
        
    def _resolve_template(self, template: str) -> str:
        """Internal template resolution."""
        if not isinstance(template, str):
            return template
            
        pattern = r'\{\{([^}]+)\}\}'
        
        def replace(match):
            ref = match.group(1).strip()
            
            # Parse default value
            if ':' in ref:
                ref_path, default = ref.split(':', 1)
            else:
                ref_path, default = ref, None
                
            # Parse scope
            if '.' in ref_path:
                scope, key = ref_path.split('.', 1)
            else:
                scope, key = "global", ref_path
                
            value = self.get(key, scope, default)
            return str(value) if value is not None else match.group(0)
            
        return re.sub(pattern, replace, template)
        
    def snapshot(self, stage: str):
        """
        Create an immutable snapshot of current context.
        
        Args:
            stage: Current stage name
        """
        snapshot = {
            'stage': stage,
            'variables': {
                k: {'value': v.value, 'scope': v.scope}
                for k, v in self._variables.items()
            }
        }
        self._snapshots.append(snapshot)
        logger.debug(f"Context snapshot created for stage: {stage}")
        
    def get_snapshots(self) -> list:
        """Get all context snapshots for audit."""
        return self._snapshots.copy()
        
    def to_dict(self) -> Dict[str, Any]:
        """Export context as dictionary."""
        return {
            'run_id': self.run_id,
            'trigger_id': self.trigger_id,
            'variables': {
                k: v.value for k, v in self._variables.items()
            },
            'snapshots': self._snapshots
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowContext':
        """Restore context from dictionary."""
        ctx = cls(data['run_id'], data.get('trigger_id'))
        for key, value in data.get('variables', {}).items():
            ctx._variables[key] = ContextVariable(value=value)
        ctx._snapshots = data.get('snapshots', [])
        return ctx


class ContextAwareEngine:
    """
    Workflow engine with dynamic context support.
    
    Wraps the existing engine to add context management.
    """
    
    def __init__(self, base_engine):
        self.base_engine = base_engine
        
    async def run_domain_workflow(
        self,
        request: DomainWorkflowRequest,
        *,
        trigger_id: Optional[str] = None,
        event_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute workflow with context management.
        """
        import uuid
        run_id = str(uuid.uuid4())
        
        # Create context
        ctx = WorkflowContext(run_id=run_id, trigger_id=trigger_id)
        
        # Set initial context
        ctx.set("domain", request.domain)
        ctx.set("platform", request.platform)
        ctx.set("run_id", run_id)
        
        if trigger_id:
            ctx.set("trigger_id", trigger_id)
            
        input_params = request.model_dump()
        for key, value in input_params.items():
            ctx.set(key, value, scope="input")
                
        if event_context:
            for key, value in event_context.items():
                ctx.set(key, value, scope="event")

        ctx.snapshot("bootstrap")

        # Execute with context
        try:
            result = await self.base_engine.run_domain_workflow(request, trigger_id=trigger_id)
            
            # Add context snapshots to result
            result['context_snapshots'] = ctx.get_snapshots()
            
            return result
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            raise
            
    async def _execute_with_context(self, ctx: WorkflowContext, domain: str, platform: str, **kwargs):
        """Execute stages with context passing."""
        # This would integrate with the existing engine
        # For now, placeholder showing context usage
        
        # Example: CFO stage
        ctx.snapshot("CFO")
        cfo_result = {"budget": 1000}  # Would call actual service
        ctx.set("budget", cfo_result["budget"], scope="CFO")
        
        # Example: Research stage using context
        ctx.snapshot("Research")
        budget = ctx.get("budget", scope="CFO")  # 1000
        research_result = {"queries": ["AI trends"]}  # Would use budget from context
        ctx.set("queries", research_result["queries"], scope="Research")
        
        # Example: Template resolution
        template = "Researching {{CFO.budget}} topics: {{Research.queries}}"
        resolved = ctx.resolve(template)
        # Result: "Researching 1000 topics: ['AI trends']"
        
        return {
            'status': 'completed',
            'run_id': ctx.run_id,
            'resolved_template': resolved
        }
