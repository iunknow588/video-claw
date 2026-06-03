"""
Trigger and workflow integration tests aligned with the current CXO workflow contract.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from departments.CEO.services.orchestration.engine import WorkflowExecutionEngine
from departments.CIO.schemas.video import DomainWorkflowRequest
from departments.CIO.services.scheduler import TriggerScanner, TriggerService
from departments.CIO.services.workflow_runs import WorkflowRunService


class TestWorkflowRunService:
    """Tests for WorkflowRunService trigger persistence."""

    @pytest.fixture
    def mock_repository(self):
        now = datetime.now(UTC)
        repo = Mock()
        repo.create_run = AsyncMock(
            return_value=SimpleNamespace(
                id=1,
                uuid="run-123",
                trace_id="trace-123",
                trigger_id="trigger-456",
                workflow_type="domain_auto_run",
                domain="科技",
                platform="douyin",
                status="pending",
                result_payload={"audience": "年轻人"},
                created_at=now,
                updated_at=now,
            )
        )
        repo.get_by_trigger_id = AsyncMock(return_value=[])
        repo.update_status = AsyncMock(return_value=None)
        return repo

    @pytest.mark.asyncio
    async def test_create_run_with_trigger_id(self, mock_repository):
        service = WorkflowRunService(repository=mock_repository)

        await service.create_run(
            trace_id="trace-123",
            workflow_type="domain_auto_run",
            domain="科技",
            platform="douyin",
            input_params={"audience": "年轻人"},
            trigger_id="trigger-456",
        )

        call_args = mock_repository.create_run.call_args.args[0]
        assert call_args["trigger_id"] == "trigger-456"
        assert call_args["result_payload"]["audience"] == "年轻人"

    @pytest.mark.asyncio
    async def test_create_run_defaults_trigger_id_to_none(self, mock_repository):
        service = WorkflowRunService(repository=mock_repository)

        await service.create_run(
            trace_id="trace-123",
            workflow_type="domain_auto_run",
            domain="科技",
            platform="douyin",
        )

        call_args = mock_repository.create_run.call_args.args[0]
        assert call_args["trigger_id"] is None


class TestWorkflowExecutionEngine:
    """Tests for the current workflow engine contract."""

    @pytest.fixture
    def mock_assembly(self):
        recorder = Mock()
        recorder.record_artifact = AsyncMock()
        recorder.record_log = AsyncMock()
        return SimpleNamespace(
            recorder=recorder,
            control_plane=Mock(),
        )

    @pytest.fixture
    def mock_run_service(self):
        service = Mock()
        service.create_run = AsyncMock(return_value=SimpleNamespace(id=1, uuid="run-123"))
        service.update_run_status = AsyncMock(return_value=None)
        return service

    @pytest.mark.asyncio
    async def test_run_domain_workflow_persists_trigger_id(self, mock_assembly, mock_run_service):
        engine = WorkflowExecutionEngine(
            assembly=mock_assembly,
            workflow_run_service=mock_run_service,
        )
        request = DomainWorkflowRequest(domain="科技", platform="douyin", audience="年轻人")

        planning_result = {
            "status": "completed",
            "notes": ["planning ok"],
            "prompt_package": {"hooks": ["反差"]},
            "prompt_bundle": {"topic": "龙虾开店"},
        }
        production_result = {
            "status": "completed",
            "notes": ["production ok"],
            "script_id": "script-1",
            "script_status": "approved",
            "video_task_id": "video-1",
            "video_status": "queued",
            "bundle": {},
        }
        qa_result = {
            "status": "passed",
            "notes": ["qa ok"],
            "qa_report": {"qa_status": "passed"},
            "bundle": {},
        }

        with (
            patch.object(
                engine,
                "_run_stage",
                new=AsyncMock(
                    side_effect=[
                        {"status": "passed", "notes": ["budget ok"]},
                        {
                            "status": "completed",
                            "notes": ["research ok"],
                            "expanded_queries": ["科技爆款"],
                            "selected_hotspots": [],
                            "bundle": {},
                        },
                        {
                            "status": "completed",
                            "notes": ["analysis ok"],
                            "analysis_reports": [],
                            "bundle": {"analysis_ids": ["analysis-1"]},
                        },
                        planning_result,
                        production_result,
                        {"status": "completed", "notes": ["publish ok"], "bundle": {"publish_result": {"status": "skipped"}}},
                    ],
                ),
            ),
            patch.object(
                engine,
                "_run_qa_stage",
                new=AsyncMock(return_value=(planning_result, production_result, qa_result)),
            ),
        ):
            result = await engine.run_domain_workflow(
                request,
                trigger_id="trigger-daily-hotspots",
            )

        create_call = mock_run_service.create_run.call_args.kwargs
        assert create_call["trigger_id"] == "trigger-daily-hotspots"
        assert result["trigger_id"] == "trigger-daily-hotspots"
        assert result["qa_status"] == "passed"

    @pytest.mark.asyncio
    async def test_run_domain_workflow_allows_manual_execution(self, mock_assembly, mock_run_service):
        engine = WorkflowExecutionEngine(
            assembly=mock_assembly,
            workflow_run_service=mock_run_service,
        )
        request = DomainWorkflowRequest(domain="科技", platform="douyin")

        with (
            patch.object(engine, "_run_stage", new=AsyncMock(side_effect=RuntimeError("stop after create_run"))),
            patch.object(engine, "_build_failure_context", new=AsyncMock(return_value={"status": "failed"})),
        ):
            with pytest.raises(RuntimeError, match="stop after create_run"):
                await engine.run_domain_workflow(request)

        create_call = mock_run_service.create_run.call_args.kwargs
        assert create_call["trigger_id"] is None


class TestTriggerScanner:
    """Tests for trigger scanner dedupe and dispatch."""

    @pytest.fixture
    def mock_engine(self):
        engine = Mock()
        engine.run_domain_workflow = AsyncMock(return_value={"status": "completed"})
        return engine

    @pytest.mark.asyncio
    async def test_fire_trigger_skips_when_within_cooldown(self, mock_engine):
        scanner = TriggerScanner(workflow_engine=mock_engine, cooldown_seconds=60)
        trigger = SimpleNamespace(
            uuid="trigger-1",
            name="test-trigger",
            domain="科技",
            platform="douyin",
            input_params={},
            cron="0 3 * * *",
            last_fired_at=datetime.now(UTC),
            next_fire_at=None,
        )
        session = Mock()
        session.execute = AsyncMock()

        await scanner._fire_trigger(trigger, session)

        mock_engine.run_domain_workflow.assert_not_called()
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_workflow_builds_domain_request_and_passes_trigger_id(self, mock_engine):
        scanner = TriggerScanner(workflow_engine=mock_engine, cooldown_seconds=0)
        trigger = SimpleNamespace(
            uuid="trigger-1",
            name="test-trigger",
            domain="科技",
            platform="douyin",
            input_params={"audience": "年轻人", "top_n": 2},
            cron="0 3 * * *",
            last_fired_at=datetime.now(UTC) - timedelta(minutes=5),
            next_fire_at=None,
        )

        await scanner._execute_workflow(trigger)

        call = mock_engine.run_domain_workflow.call_args
        request = call.args[0]
        assert isinstance(request, DomainWorkflowRequest)
        assert request.domain == "科技"
        assert request.top_n == 2
        assert request.audience == "年轻人"
        assert call.kwargs["trigger_id"] == "trigger-1"


class TestTriggerService:
    """Tests for TriggerService CRUD behavior against the current DB runtime entry."""

    @pytest.mark.asyncio
    async def test_create_trigger_uses_database_runtime_session_factory(self):
        service = TriggerService()
        session = MagicMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = False
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session_factory = Mock(return_value=session)

        with patch(
            "departments.CIO.services.scheduler.database_runtime.session_factory",
            return_value=session_factory,
        ):
            trigger = await service.create_trigger(
                name="daily-hotspots",
                cron="0 3 * * *",
                domain="科技",
                platform="douyin",
                input_params={"audience": "年轻人"},
                enabled=True,
            )

        assert trigger.name == "daily-hotspots"
        assert trigger.platform == "douyin"
        session.add.assert_called_once()
        session.commit.assert_awaited_once()


class TestAlembicMigration:
    """Tests for the trigger migration location and metadata."""

    def test_trigger_migration_exists_in_alembic_versions(self):
        migration_path = Path("src/alembic/versions/20260603_add_trigger_id.py")
        assert migration_path.exists()

        spec = importlib.util.spec_from_file_location("trigger_migration", migration_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module.revision == "20260603_add_trigger_id"
        assert module.down_revision == "20260602_0006"
