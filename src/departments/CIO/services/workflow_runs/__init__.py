"""
Workflow run service.
"""
from typing import Optional, Dict, Any
from datetime import UTC, datetime

from departments.CIO.models.workflow import WorkflowRun
from departments.CIO.db.session import database_runtime
from departments.CIO.services.data_access.workflow_repository import WorkflowRepository as SessionWorkflowRepository


class WorkflowRunService:
    """Service for managing workflow runs."""
    
    def __init__(self, session=None, repository=None):
        self.repository = repository or (
            SessionWorkflowRepository(session) if session is not None else WorkflowRunRepository()
        )
    
    async def create_run(
        self,
        trace_id: str,
        workflow_type: str,
        domain: str,
        platform: str,
        input_params: Optional[Dict[str, Any]] = None,
        trigger_id: Optional[str] = None,
        status: str = 'pending'
    ) -> WorkflowRun:
        """
        Create a new workflow run.
        
        Args:
            trace_id: Trace ID for tracking
            workflow_type: Type of workflow
            domain: Domain for workflow
            platform: Platform for workflow
            input_params: Optional input parameters
            trigger_id: Optional trigger ID if triggered by scheduler
            status: Initial status
            
        Returns:
            Created WorkflowRun instance
        """
        run = await self.repository.create_run({
            'trace_id': trace_id,
            'workflow_type': workflow_type,
            'domain': domain,
            'platform': platform,
            'status': status,
            'trigger_id': trigger_id,
            'result_payload': input_params or {},
            'audience': (input_params or {}).get('audience'),
            'publish_goal': (input_params or {}).get('publish_goal'),
            'content_type': (input_params or {}).get('content_type'),
            'style': (input_params or {}).get('style'),
            'video_style': (input_params or {}).get('video_style'),
            'duration': (input_params or {}).get('duration'),
            'created_at': datetime.now(UTC),
            'updated_at': datetime.now(UTC),
        })
        return run
    
    async def get_run_by_id(self, run_id: int) -> Optional[WorkflowRun]:
        """Get workflow run by ID."""
        if hasattr(self.repository, "get_run_by_id"):
            return await self.repository.get_run_by_id(run_id)
        return await self.repository.get_by_id(run_id)

    async def get_by_uuid(self, workflow_run_id: str) -> Optional[WorkflowRun]:
        """Get workflow run by UUID."""
        if hasattr(self.repository, "get_run_by_uuid"):
            return await self.repository.get_run_by_uuid(workflow_run_id)
        return None

    async def list_runs(
        self,
        *,
        limit: int = 50,
        domain: str | None = None,
        platform: str | None = None,
        status: str | None = None,
    ) -> list[WorkflowRun]:
        """List workflow runs with common filters."""
        if hasattr(self.repository, "list_runs"):
            return await self.repository.list_runs(
                limit=limit,
                domain=domain,
                platform=platform,
                status=status,
            )
        return []
    
    async def get_runs_by_trigger(
        self,
        trigger_id: str,
        status: Optional[str] = None,
        limit: int = 100
    ) -> list[WorkflowRun]:
        """
        Get workflow runs by trigger ID.
        
        Args:
            trigger_id: Trigger ID
            status: Optional status filter
            limit: Maximum results
            
        Returns:
            List of workflow runs
        """
        if hasattr(self.repository, "get_runs_by_trigger"):
            return await self.repository.get_runs_by_trigger(trigger_id, status=status, limit=limit)
        return await self.repository.get_by_trigger_id(trigger_id, status, limit)
    
    async def update_run_status(
        self,
        run_id: int,
        status: str,
        result_payload: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> WorkflowRun:
        """Update workflow run status."""
        if hasattr(self.repository, "get_run_by_id") and hasattr(self.repository, "update_run"):
            run = await self.repository.get_run_by_id(run_id)
            if not run:
                return None
            updates: Dict[str, Any] = {
                "status": status,
                "updated_at": datetime.now(UTC),
            }
            if result_payload is not None:
                updates["result_payload"] = result_payload
            if error_message is not None:
                updates["error_message"] = error_message
            return await self.repository.update_run(run, updates)
        return await self.repository.update_status(
            run_id,
            status,
            result_payload,
            error_message=error_message,
        )


class WorkflowRunRepository:
    """Repository for workflow run persistence."""
    
    async def create_run(self, data: Dict[str, Any]) -> WorkflowRun:
        """Create workflow run in database."""
        async with database_runtime.session_factory()() as session:
            run = WorkflowRun(**data)
            session.add(run)
            await session.commit()
            await session.refresh(run)
            return run
    
    async def get_by_id(self, run_id: int) -> Optional[WorkflowRun]:
        """Get workflow run by ID."""
        async with database_runtime.session_factory()() as session:
            result = await session.get(WorkflowRun, run_id)
            return result
    
    async def get_by_trigger_id(
        self,
        trigger_id: str,
        status: Optional[str] = None,
        limit: int = 100
    ) -> list[WorkflowRun]:
        """Get workflow runs by trigger ID with optional status filter."""
        async with database_runtime.session_factory()() as session:
            from sqlalchemy import select
            
            query = select(WorkflowRun).where(
                WorkflowRun.trigger_id == trigger_id
            ).order_by(WorkflowRun.created_at.desc()).limit(limit)
            
            if status:
                query = query.where(WorkflowRun.status == status)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def update_status(
        self,
        run_id: int,
        status: str,
        result_payload: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> WorkflowRun:
        """Update workflow run status."""
        async with database_runtime.session_factory()() as session:
            run = await session.get(WorkflowRun, run_id)
            if run:
                run.status = status
                run.updated_at = datetime.now(UTC)
                if result_payload is not None:
                    run.result_payload = result_payload
                if error_message is not None:
                    run.error_message = error_message
                await session.commit()
                await session.refresh(run)
            return run
