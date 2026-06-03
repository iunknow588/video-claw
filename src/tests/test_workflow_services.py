from datetime import datetime
from types import SimpleNamespace

import pytest

from departments.CAO.service import CAOConsoleService
from departments.CEO.core.config import settings
from departments.CEO.services.control_plane import control_plane
from departments.CEO.services.orchestration import PipelineContext, PipelineResult
from departments.CEO.services.orchestration.assembly import WorkflowAssembly
from departments.CEO.services.orchestration.domains.analysis_pipeline import AnalysisPipeline
from departments.CEO.services.orchestration.domains.finance_gate import FinanceGate
from departments.CEO.services.orchestration.domains.production_pipeline import ProductionPipeline
from departments.CEO.services.orchestration.domains.publish_pipeline import PublishPipeline
from departments.CEO.services.orchestration.domains.qa_pipeline import QAPipeline
from departments.CEO.services.orchestration.domains.rd_pipeline import RDPipeline
from departments.CEO.services.orchestration.domains.research_pipeline import ResearchPipeline
from departments.CEO.services.orchestration.engine import WorkflowExecutionEngine
from departments.CEO.services.orchestration.recorder import WorkflowRecorder
from departments.CEO.services.orchestration.reroute import QARerouteService, QARerouteStrategy
from departments.CEO.skills.base import BaseSkill
from departments.CEO.skills.runtime import SkillRuntimeManager
from departments.CEO.leaders.departments import LEADER_CLASS_MAP, build_department_leader
from departments.CIO.models.artifact import ArtifactRecord
from departments.CIO.models.analysis import AnalysisReport
from departments.CIO.models.cost import CostRecord
from departments.CIO.models.hotspot import HotspotItem
from departments.CIO.models.image import ImageTask
from departments.CIO.models.information_event import InformationEvent
from departments.CIO.models.review import ReviewRecord
from departments.CIO.models.script import Script
from departments.CIO.models.step_log import WorkflowStepLog
from departments.CIO.models.workflow import WorkflowRun, WorkflowTrigger
from departments.CIO.services.scheduler import TriggerScanner
from departments.CIO.services.workflow_runs import WorkflowRunService
from departments.CTO.services.ai_clients import (
    AIProviderResult,
    SeedanceClient,
    TokenUsage,
    build_xfyun_maas_client,
    get_ai_provider_config,
    should_use_placeholder,
)
from departments.CCO.services.content_creation import AIAnalysisService
from departments.CIO.services.knowledge import CIOInformationService
from departments.CSO.services.hotspot import HotspotService
from departments.CFO.services.finance import FinanceService
from departments.COO.services.script_management import ScriptService
from departments.COO.services.asset_management import ImageGenerationService
from departments.CIO.services.operations import OperationsService
from departments.CIO.services.storage import (
    LocalVideoStorage,
    S3CompatibleVideoStorage,
    asset_exists,
    describe_video_storage,
    get_video_storage,
    get_storage_runtime,
)
from departments.COO.services.video_production import VideoService
from departments.CIO.schemas.video import DomainWorkflowRequest, HotspotCreate


@pytest.mark.asyncio
async def test_hotspot_search_and_fetch(session):
    service = HotspotService(session)
    await service.create(
        HotspotCreate(
            platform="xigua",
            content_id="abc123",
            title="Lobster operations breakdown",
            author="tester",
            category="business",
        )
    )
    await session.commit()

    results = await service.search("Lobster")
    assert len(results) == 1
    assert results[0].content_id == "abc123"


def test_cao_console_service_uses_friendly_fallback_for_corrupted_domain():
    service = CAOConsoleService(SimpleNamespace())
    run = SimpleNamespace(
        uuid="run-1",
        domain="??????",
        publish_goal=None,
        platform="douyin",
        workflow_type="domain_auto_run",
        status="completed",
        duration=20,
        created_at=datetime(2026, 6, 2, 1, 12),
        trace_id="trace-1",
        result_payload={"qa_status": "passed"},
    )

    payload = service._serialize_public_run(run)

    assert payload["domain"] == "??????"
    assert payload["display_domain"] == "抖音任务 06-02 01:12"
    assert payload["workflow_type_label"] == "自动制作流程"


@pytest.mark.asyncio
async def test_hotspot_fetch_refreshes_existing_payload(session):
    service = HotspotService(session)
    item = await service.create(
        HotspotCreate(
            platform="douyin",
            content_id="douyin-refresh-1",
            title="old title",
            author="old_author",
            tags=["mvp"],
        )
    )
    await session.flush()

    async def fake_fetch_from_provider(platform, keyword, count):
        return [
            {
                "platform": "douyin",
                "content_id": "douyin-refresh-1",
                "title": "new title",
                "author": "new_author",
                "author_id": "new_author_id",
                "url": "https://example.com/douyin/new/1",
                "cover_image": "https://example.com/assets/douyin/new-1.jpg",
                "video_url": None,
                "view_count": 99999,
                "like_count": 8888,
                "comment_count": 777,
                "share_count": 66,
                "category": "general",
                "tags": ["lobster", "douyin", "mvp", "mock"],
                "duration": 42,
                "fetched_at": "2026-06-02T00:00:00+00:00",
            }
        ]

    service._fetch_from_provider = fake_fetch_from_provider  # type: ignore[method-assign]

    refreshed = await service.fetch_hotspots(SimpleNamespace(platform="douyin", keyword="lobster", count=1))
    assert refreshed[0].uuid == item.uuid
    assert refreshed[0].title == "new title"
    assert refreshed[0].author == "new_author"
    assert refreshed[0].view_count == 99999
    assert refreshed[0].fetched_at == "2026-06-02T00:00:00+00:00"


@pytest.mark.asyncio
async def test_analysis_script_video_flow_creates_audit_records(session):
    hotspot = HotspotItem(
        platform="douyin",
        content_id="dy-1",
        title="Top lobster short-video script",
        author="creator",
        category="food",
        view_count=12345,
        like_count=888,
    )
    session.add(hotspot)
    await session.flush()

    analysis = await AIAnalysisService(session).analyze_content(hotspot)
    assert isinstance(analysis, AnalysisReport)

    script = await ScriptService(session).generate_script(
        analysis=analysis,
        content_type="knowledge",
        style="fast",
        topic="Lobster topic plan",
        duration=60,
    )
    assert isinstance(script, Script)
    assert script.status == "pending_review"

    script_service = ScriptService(session)
    reviewed_script = await script_service.review_script(script.uuid, True, "approved")
    assert reviewed_script.status == "approved"

    video_service = VideoService(session)
    task = await video_service.create_task(script=reviewed_script, style="realistic")
    await video_service.process_task(task.uuid)
    reviewed_task = await video_service.review_task(task.uuid, True, "video approved")
    assert reviewed_task.status == "approved"

    await session.commit()

    cost_records = (await session.execute(CostRecord.__table__.select())).all()
    review_records = (await session.execute(ReviewRecord.__table__.select())).all()

    assert len(cost_records) == 3
    assert len(review_records) == 2


@pytest.mark.asyncio
async def test_script_service_normalizes_scene_shape(session, monkeypatch):
    hotspot = HotspotItem(
        platform="douyin",
        content_id="dy-script-normalize-1",
        title="Scene shape case",
        author="creator",
        category="knowledge",
    )
    session.add(hotspot)
    await session.flush()

    analysis = AnalysisReport(
        hotspot_id=hotspot.uuid,
        analysis_type="comprehensive",
        framework_summary="normalize scenes",
        reusable_elements=["hook"],
    )
    session.add(analysis)
    await session.flush()

    service = ScriptService(session)
    monkeypatch.setattr(settings.ai_providers.runtime, "use_placeholder_when_unconfigured", False)

    async def fake_chat_json(*, model: str, prompt: str, system_prompt: str, temperature: float = 0.7):
        return AIProviderResult(
            data={
                "title": "Normalized Script",
                "scenes": [
                    {"time": "00:00-00:05", "shot": "macro close-up", "voiceover": "intro", "caption": "hello"},
                    {"timing": "00:05-00:10", "visuals": "wide shot", "audio": "detail", "text": "world"},
                ],
                "hook": "hook",
                "cta": "cta",
                "tags": ["one"],
                "similarity_score": 0.12,
                "cost": 0.01,
            },
            usage=TokenUsage(input_tokens=10, output_tokens=20, total_tokens=30),
            raw_response={},
        )

    monkeypatch.setattr(service.client, "chat_json", fake_chat_json)
    script = await service.generate_script(
        analysis=analysis,
        content_type="knowledge",
        style="clean",
        topic="normalize",
        duration=10,
    )

    assert script.scenes[0]["timing"] == "00:00-00:05"
    assert script.scenes[0]["visuals"] == "macro close-up"
    assert script.scenes[0]["audio"] == "intro"
    assert script.scenes[0]["text"] == "hello"
    assert script.scenes[1]["timing"] == "00:05-00:10"


@pytest.mark.asyncio
async def test_image_generation_service_creates_placeholder_asset(session, monkeypatch):
    monkeypatch.setattr(settings.ai_providers.hidream, "app_id", "")
    monkeypatch.setattr(settings.ai_providers.hidream, "api_key", "")
    monkeypatch.setattr(settings.ai_providers.hidream, "api_secret", "")

    service = ImageGenerationService(session)
    task = await service.create_task(
        script_id=None,
        prompt="龙虾门店运营封面图，强对比构图",
        negative_prompt="模糊, 低清晰度",
        aspect_ratio="9:16",
        resolution="2k",
        image_count=1,
        use_case="cover",
    )
    processed = await service.process_task(task.uuid)
    await session.commit()

    assert isinstance(processed, ImageTask)
    assert processed.status == "completed"
    assert processed.primary_image_url is not None
    assert processed.primary_image_url.endswith(".png")
    assert processed.result_payload["mode"] == "placeholder"


@pytest.mark.asyncio
async def test_analysis_service_preserves_provider_token_usage(session, monkeypatch):
    hotspot = HotspotItem(
        platform="douyin",
        content_id="dy-token-1",
        title="Token usage case",
        author="creator",
        category="food",
    )
    session.add(hotspot)
    await session.flush()

    service = AIAnalysisService(session)
    monkeypatch.setattr(settings.ai_providers.runtime, "use_placeholder_when_unconfigured", False)

    async def fake_chat_json(*, model: str, prompt: str, system_prompt: str, temperature: float = 0.3):
        return AIProviderResult(
            data={
                "content_structure": {"beats": 3},
                "emotion_curve": {"curve": "rise"},
                "hook_design": {"hook": "strong"},
                "framework_summary": "Token aware summary",
                "reusable_elements": ["hook"],
                "risk_warnings": [],
                "cost": 0.12,
            },
            usage=TokenUsage(input_tokens=21, output_tokens=13, total_tokens=34),
            raw_response={"usage": {"total_tokens": 34}},
        )

    monkeypatch.setattr(service.client, "chat_json", fake_chat_json)
    report = await service.analyze_content(hotspot)
    await session.commit()

    assert getattr(report, "_token_usage")["total_tokens"] == 34
    cost_records = (await session.execute(CostRecord.__table__.select())).all()
    assert cost_records[-1]._mapping["metadata_json"]["token_usage"]["input_tokens"] == 21


@pytest.mark.asyncio
async def test_operations_summary_contains_review_and_cost_counts(session):
    hotspot = HotspotItem(
        platform="xiaohongshu",
        content_id="xhs-1",
        title="Lobster store experience",
        author="creator",
        category="knowledge",
    )
    session.add(hotspot)
    await session.flush()

    analysis = await AIAnalysisService(session).analyze_content(hotspot)
    script_service = ScriptService(session)
    script = await script_service.generate_script(
        analysis=analysis,
        content_type="knowledge",
        style="clean",
        topic="Lobster operations",
        duration=45,
    )
    script = await script_service.review_script(script.uuid, True, "ok")
    video_service = VideoService(session)
    task = await video_service.create_task(script=script, style="realistic")
    await video_service.process_task(task.uuid)
    await video_service.review_task(task.uuid, False, "needs rework")
    await session.commit()

    summary = await OperationsService(session).build_summary()
    assert summary["counts"]["hotspots"] == 1
    assert summary["counts"]["reviews"] == 2
    assert summary["counts"]["cost_records"] == 3
    assert summary["cost_breakdown"]["total"] > 0
    assert summary["budget_usage_ratio"] == round(
        summary["cost_breakdown"]["total"] / settings.DAILY_BUDGET if settings.DAILY_BUDGET else 0.0,
        4,
    )
    assert summary["budget_alert_level"] in {"normal", "warning", "alert", "critical"}


@pytest.mark.asyncio
async def test_finance_service_exposes_budget_alert_level(session):
    hotspot = HotspotItem(
        platform="douyin",
        content_id="finance-1",
        title="Finance summary case",
        author="creator",
        category="knowledge",
    )
    session.add(hotspot)
    await session.flush()

    analysis = await AIAnalysisService(session).analyze_content(hotspot)
    script = await ScriptService(session).generate_script(
        analysis=analysis,
        content_type="knowledge",
        style="clean",
        topic="Finance workflow",
        duration=30,
    )
    await session.commit()

    summary = await FinanceService(session).build_summary()

    assert summary["daily_budget"] == settings.DAILY_BUDGET
    assert summary["actual_spend"] > 0
    assert summary["alert_level"] in {"normal", "warning", "alert", "critical"}


@pytest.mark.asyncio
async def test_cio_information_service_persists_artifacts_and_knowledge(session):
    service = CIOInformationService(session)

    artifact = await service.store_artifact(
        trace_id="trace-cio-1",
        artifact_type="research.bundle",
        payload={"selected_hotspots": 3},
        source="lead.research",
    )
    event = await service.record_event(
        trace_id="trace-cio-1",
        level="info",
        message="artifact stored",
        context={"artifact_type": "research.bundle"},
    )
    knowledge_asset = await service.upsert_knowledge_asset(
        category="templates",
        asset={"asset_id": "template-cio-test", "title": "Test Template", "summary": "template summary"},
    )
    await session.commit()

    restored = await service.retrieve_artifact(trace_id="trace-cio-1", artifact_type="research.bundle")
    knowledge_assets = await service.list_knowledge_assets("templates")
    summary = await service.build_summary()

    assert artifact["artifact_type"] == "research.bundle"
    assert event["message"] == "artifact stored"
    assert knowledge_asset["asset_id"] == "template-cio-test"
    assert restored is not None
    assert restored["payload"]["selected_hotspots"] == 3
    assert any(item["asset_id"] == "template-cio-test" for item in knowledge_assets["templates"])
    assert summary["artifact_count"] >= 1
    assert summary["knowledge_asset_count"] >= 1


@pytest.mark.asyncio
async def test_workflow_recorder_routes_artifact_events_into_cio_event_store(session):
    assembly = WorkflowAssembly(session)
    recorder = WorkflowRecorder(assembly)

    await recorder.record_artifact(
        trace_id="trace-event-artifact-1",
        source="lead.research",
        artifact_type="research.bundle",
        payload={"selected_hotspots": 2},
    )
    await session.commit()

    artifact_records = (await session.execute(ArtifactRecord.__table__.select())).all()
    information_events = (await session.execute(InformationEvent.__table__.select())).all()
    step_logs = (await session.execute(WorkflowStepLog.__table__.select())).all()

    assert artifact_records[-1]._mapping["artifact_type"] == "research.bundle"
    assert artifact_records[-1]._mapping["source"] == "lead.research"
    assert information_events[-1]._mapping["message"] == "research.bundle stored"
    assert len(step_logs) == 0


@pytest.mark.asyncio
async def test_workflow_recorder_routes_trace_events_into_trace_collector(session):
    assembly = WorkflowAssembly(session)
    recorder = WorkflowRecorder(assembly)
    skill = assembly.get_skill("ceo.workflow")

    result = await recorder.call_skill(
        trace_id="trace-event-trace-1",
        parent_id="ceo.workflow",
        skill=skill,
        input_bundle={"trace_id": "trace-event-trace-1", "domain": "lobster", "platform": "douyin"},
        method_name="build_plan",
    )
    await session.commit()

    assert result.descriptor.name == "ceo.workflow"
    step_logs = (await session.execute(WorkflowStepLog.__table__.select())).all()
    information_events = (await session.execute(InformationEvent.__table__.select())).all()

    assert len(step_logs) == 2
    assert step_logs[0]._mapping["event_type"] == "start"
    assert step_logs[1]._mapping["event_type"] == "finish"
    assert information_events[0]._mapping["message"] == "ceo.workflow:start"
    assert information_events[1]._mapping["message"] == "ceo.workflow:finish"


@pytest.mark.asyncio
async def test_local_video_storage_returns_media_url(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.storage, "media_root", str(tmp_path))
    monkeypatch.setattr(settings.storage, "media_url_prefix", "/media")
    monkeypatch.setattr(settings.storage, "media_base_url", None)

    storage = LocalVideoStorage()
    url = await storage.save_video(task_uuid="task-001", content=b"demo-bytes")

    assert url == "/media/videos/task-001.mp4"
    assert (tmp_path / "videos" / "task-001.mp4").exists()


@pytest.mark.asyncio
async def test_local_video_storage_prefers_media_base_url(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.storage, "media_root", str(tmp_path))
    monkeypatch.setattr(settings.storage, "media_url_prefix", "/media")
    monkeypatch.setattr(settings.storage, "media_base_url", "https://cdn.example.com/media")

    storage = LocalVideoStorage()
    url = await storage.save_video(task_uuid="task-002", content=b"demo-bytes")

    assert url == "https://cdn.example.com/media/videos/task-002.mp4"


def test_storage_factory_supports_s3_backend(monkeypatch):
    monkeypatch.setattr(settings.storage, "video_backend", "s3_compatible")
    storage = get_video_storage()
    assert isinstance(storage, S3CompatibleVideoStorage)


def test_describe_video_storage_for_s3_backend(monkeypatch):
    monkeypatch.setattr(settings.storage, "video_backend", "s3_compatible")
    monkeypatch.setattr(settings.storage, "media_url_prefix", "/media")
    monkeypatch.setattr(settings.storage.s3_compatible, "bucket", "lobster-videos")
    monkeypatch.setattr(settings.storage.s3_compatible, "access_key_id", "demo-ak")
    monkeypatch.setattr(settings.storage.s3_compatible, "secret_access_key", "demo-sk")
    monkeypatch.setattr(settings.storage.s3_compatible, "endpoint_url", "https://s3.example.com")
    monkeypatch.setattr(settings.storage.s3_compatible, "region", "ap-east-1")
    monkeypatch.setattr(settings.storage.s3_compatible, "object_prefix", "videos")
    monkeypatch.setattr(settings.storage.s3_compatible, "public_base_url", "https://cdn.example.com/videos")

    result = describe_video_storage()

    assert result["backend"] == "s3_compatible"
    assert result["configured"] is True
    assert result["bucket"] == "lobster-videos"
    assert result["public_base_url"] == "https://cdn.example.com/videos"


def test_ai_provider_factory_uses_central_runtime_policy(monkeypatch):
    monkeypatch.setattr(settings.ai_providers.xfyun_maas, "api_key", "")
    monkeypatch.setattr(settings.ai_providers.xfyun_maas, "base_url", "https://maas.example.com/v2")
    monkeypatch.setattr(settings.ai_providers.xfyun_maas, "model", "xfyun-test")
    monkeypatch.setattr(settings.ai_providers.xfyun_maas, "resource_id", "resource-1")
    monkeypatch.setattr(settings.ai_providers.runtime, "http_timeout", 12.5)
    monkeypatch.setattr(settings.ai_providers.runtime, "max_retries", 5)
    monkeypatch.setattr(settings.ai_providers.runtime, "use_placeholder_when_unconfigured", True)

    provider = get_ai_provider_config("xfyun_maas")
    client = build_xfyun_maas_client(provider)

    assert provider.provider == "xfyun_maas"
    assert provider.model == "xfyun-test"
    assert provider.resource_id == "resource-1"
    assert provider.is_configured is False
    assert should_use_placeholder(provider) is True
    assert client.timeout == 12.5
    assert client.max_retries == 5


@pytest.mark.asyncio
async def test_xfyun_client_repairs_malformed_json(monkeypatch):
    monkeypatch.setattr(settings.ai_providers.xfyun_maas, "api_key", "demo-key")
    monkeypatch.setattr(settings.ai_providers.xfyun_maas, "base_url", "https://maas.example.com/v2")
    monkeypatch.setattr(settings.ai_providers.xfyun_maas, "model", "astron-code-latest")
    monkeypatch.setattr(settings.ai_providers.xfyun_maas, "resource_id", "")

    provider = get_ai_provider_config("xfyun_maas")
    client = build_xfyun_maas_client(provider)
    responses = iter(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"title":"bad","audio":"Voiceover: "broken""}',
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 12, "total_tokens": 22},
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"title":"bad","audio":"Voiceover: broken"}',
                        }
                    }
                ],
                "usage": {"prompt_tokens": 6, "completion_tokens": 8, "total_tokens": 14},
            },
        ]
    )

    async def fake_post_json(*, path, payload, headers=None):
        return next(responses)

    monkeypatch.setattr(client, "_post_json", fake_post_json)

    result = await client.chat_json(
        model=provider.model,
        prompt="Generate JSON",
        system_prompt="Return JSON only",
        temperature=0.1,
    )

    assert result.data["audio"] == "Voiceover: broken"
    assert result.usage.total_tokens == 36


@pytest.mark.asyncio
async def test_seedance_client_uses_task_create_and_poll(monkeypatch):
    client = SeedanceClient(
        api_key="demo-key",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        timeout=1,
        max_retries=0,
    )

    async def fake_post_json(self, *, path, payload, headers=None):
        assert path == "/contents/generations/tasks"
        assert payload["model"] == "doubao-seedance-2-0-260128"
        assert payload["content"][0]["type"] == "text"
        assert payload["ratio"] == "9:16"
        return {"id": "task-123", "status": "submitted"}

    query_calls = {"count": 0}

    async def fake_get_json(self, *, path, headers=None):
        assert path == "/contents/generations/tasks/task-123"
        query_calls["count"] += 1
        if query_calls["count"] == 1:
            return {"id": "task-123", "status": "running"}
        return {"id": "task-123", "status": "succeeded", "video_url": "https://example.com/video.mp4"}

    monkeypatch.setattr(SeedanceClient, "_post_json", fake_post_json, raising=False)
    monkeypatch.setattr(SeedanceClient, "_get_json", fake_get_json, raising=False)

    result = await client.create_video(
        model="doubao-seedance-2-0-260128",
        prompt="demo prompt",
        duration=5,
        ratio="9:16",
    )

    assert result.data["video_url"] == "https://example.com/video.mp4"
    assert query_calls["count"] == 2


def test_video_service_extracts_nested_provider_video_result(session):
    service = VideoService(session)

    assert service._extract_provider_video_result({"video_url": "https://example.com/a.mp4"})["video_url"] == "https://example.com/a.mp4"
    assert service._extract_provider_video_result({"data": {"video_url": "https://example.com/b.mp4"}})["video_url"] == "https://example.com/b.mp4"
    assert service._size_to_ratio("1080x1920") == "9:16"
    assert service._size_to_ratio("1920x1080") == "16:9"


def test_storage_runtime_centralizes_media_path_resolution(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.storage, "media_root", str(tmp_path))
    monkeypatch.setattr(settings.storage, "media_url_prefix", "/media")
    monkeypatch.setattr(settings.storage, "media_base_url", None)

    runtime = get_storage_runtime()
    video_path = runtime.resolve_path("videos", "runtime-test.mp4")
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"runtime")

    assert runtime.build_public_url("videos/runtime-test.mp4") == "/media/videos/runtime-test.mp4"
    assert asset_exists("/media/videos/runtime-test.mp4") is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("pipeline_class", "input_bundle", "payload", "expected_status", "expected_kwargs"),
    [
        (
            FinanceGate,
            {},
            {
                "finance_estimate": {"estimated_cost": 1.2},
                "finance_check": {"passed": True},
                "receipt": {"transaction_id": "tx-1"},
                "notes": ["finance_reserved=1.2"],
            },
            "success",
            lambda context, input_bundle: {
                "trace_id": context.trace_id,
                "workflow_run_id": context.workflow_run_id,
                "request": context.request,
            },
        ),
        (
            ResearchPipeline,
            {},
            {
                "expanded_queries": ["lobster"],
                "selected_hotspots": [{"uuid": "hotspot-1"}],
                "bundle": {"selected_hotspots": [{"uuid": "hotspot-1"}]},
                "notes": ["research_selected=1"],
            },
            "success",
            lambda context, input_bundle: {
                "trace_id": context.trace_id,
                "request": context.request,
            },
        ),
        (
            AnalysisPipeline,
            {"hotspots": [{"uuid": "hotspot-1"}]},
            {
                "analysis_reports": ["analysis-model"],
                "bundle": {"analysis_ids": ["analysis-1"]},
                "notes": ["analysis_count=1"],
            },
            "success",
            lambda context, input_bundle: {
                "trace_id": context.trace_id,
                "hotspots": input_bundle["hotspots"],
            },
        ),
        (
            RDPipeline,
            {"hotspots": [{"uuid": "hotspot-1"}], "analyses": ["analysis-model"]},
            {
                "prompt_package": {"script_topic": "lobster topic"},
                "prompt_bundle": {"script_topic": "lobster topic"},
                "title_candidates": ["title"],
                "validation": {"passed": True},
                "version": 1,
                "version_bundle": {"version": 1},
                "notes": ["prompt_version=1"],
            },
            "success",
            lambda context, input_bundle: {
                "trace_id": context.trace_id,
                "request": context.request,
                "domain": context.request.domain,
                "hotspots": input_bundle["hotspots"],
                "analyses": input_bundle["analyses"],
            },
        ),
        (
            ProductionPipeline,
            {"planning_bundle": {"prompt_bundle": {}}, "primary_analysis": "analysis-model", "qa_feedback": "tighten"},
            {
                "script": "script-model",
                "video_task": None,
                "trace_bundle": {"render_bundle": {"render_mode": "preview_placeholder"}},
                "bundle": {"script": "script-model"},
                "notes": ["video_not_requested"],
            },
            "success",
            lambda context, input_bundle: {
                "trace_id": context.trace_id,
                "request": context.request,
                "planning_bundle": input_bundle["planning_bundle"],
                "primary_analysis": input_bundle["primary_analysis"],
                "qa_feedback": input_bundle["qa_feedback"],
            },
        ),
        (
            QAPipeline,
            {
                "prompt_bundle": {"script_topic": "lobster"},
                "analysis_bundle": {"analysis_ids": ["analysis-1"]},
                "production_bundle": {"script": "script-model"},
            },
            {
                "qa_report": {"qa_status": "rework", "recommendation": "retry"},
                "bundle": {"checks": []},
                "notes": ["qa_status=rework"],
            },
            "rework",
            lambda context, input_bundle: {
                "trace_id": context.trace_id,
                "request": context.request,
                "prompt_bundle": input_bundle["prompt_bundle"],
                "analysis_bundle": input_bundle["analysis_bundle"],
                "production_bundle": input_bundle["production_bundle"],
            },
        ),
        (
            PublishPipeline,
            {
                "production_bundle": {"script": "script-model"},
                "qa_bundle": {"qa_report": {"qa_status": "passed"}},
            },
            {
                "bundle": {"publish_result": {"status": "published"}},
                "notes": ["publish_status=published"],
            },
            "success",
            lambda context, input_bundle: {
                "trace_id": context.trace_id,
                "request": context.request,
                "production_bundle": input_bundle["production_bundle"],
                "qa_bundle": input_bundle["qa_bundle"],
            },
        ),
    ],
)
async def test_department_pipelines_share_standard_contract(
    session,
    pipeline_class,
    input_bundle,
    payload,
    expected_status,
    expected_kwargs,
):
    assembly = WorkflowAssembly(session)
    context = PipelineContext(
        trace_id="trace-pipeline-contract-1",
        workflow_run_id="run-pipeline-contract-1",
        request=DomainWorkflowRequest(
            domain="lobster",
            platform="douyin",
            hotspot_count=6,
            top_n=2,
            content_type="knowledge",
            style="clean",
            duration=30,
        ),
    )
    pipeline = pipeline_class(assembly)
    captured_kwargs = {}

    async def fake_execute(**kwargs):
        captured_kwargs.update(kwargs)
        return payload

    pipeline.use_case.execute = fake_execute

    result = await pipeline.run(context, input_bundle)

    expected_bundle = dict(payload)
    expected_notes = expected_bundle.pop("notes")

    assert isinstance(result, PipelineResult)
    assert result.status == expected_status
    assert result.bundle == expected_bundle
    assert result.notes == expected_notes
    assert captured_kwargs == expected_kwargs(context, input_bundle)


def test_control_plane_exposes_balanced_qa_reroute_policy():
    control_plane.reset_defaults()

    policy = control_plane.get_qa_reroute_policy()

    assert policy["strategy"] == "balanced"
    assert policy["mapping"]["passed"] == "lead.publish"
    assert policy["mapping"]["retry_production"] == "lead.production"
    assert policy["mapping"]["retry_research_development"] == "lead.research_development"


@pytest.mark.parametrize(
    ("strategy", "qa_report", "expected_target"),
    [
        ("aggressive", {"qa_status": "failed", "failed_dimensions": ["gene_alignment"]}, "lead.production"),
        ("conservative", {"qa_status": "failed", "failed_dimensions": ["video_quality"]}, "lead.research_development"),
        ("balanced", {"qa_status": "failed", "failed_dimensions": ["gene_alignment"]}, "lead.research_development"),
        ("balanced", {"qa_status": "failed", "failed_dimensions": ["render_output"]}, "lead.production"),
    ],
)
def test_qa_reroute_service_applies_configured_strategy(strategy, qa_report, expected_target):
    service = QARerouteService(
        SimpleNamespace(
            get_qa_reroute_policy=lambda: {
                "strategy": strategy,
                "mapping": {
                    "passed": "lead.publish",
                    "retry_production": "lead.production",
                    "retry_research_development": "lead.research_development",
                },
            }
        )
    )

    decision = service.determine_reroute(qa_report)

    assert decision.strategy == strategy
    assert decision.target == expected_target


def test_qa_reroute_service_supports_dynamic_strategy_injection():
    class PrefixStrategy(QARerouteStrategy):
        name = "prefix"

        def determine_route_key(self, qa_report):
            if qa_report.get("qa_status") == "passed":
                return "passed"
            return f"retry_{qa_report['failed_dimensions'][0]}"

    service = QARerouteService(
        SimpleNamespace(
            get_qa_reroute_policy=lambda: {
                "strategy": "prefix",
                "mapping": {
                    "passed": "lead.publish",
                    "retry_production": "lead.production",
                    "retry_research_development": "lead.research_development",
                },
            }
        ),
        strategy_registry={"prefix": PrefixStrategy},
    )

    decision = service.determine_reroute({"qa_status": "failed", "failed_dimensions": ["production"]})

    assert decision.strategy == "prefix"
    assert decision.target == "lead.production"


def test_leader_reports_share_consistent_contract():
    for leader_name in LEADER_CLASS_MAP:
        leader = build_department_leader(
            leader_name,
            {
                "display_name": leader_name,
                "description": "test",
            },
        )
        report = leader.build_report()
        periodic_report = leader.build_periodic_report({})

        assert "department_type" in report
        assert "focus_metrics" in report
        assert "managed_capabilities" in report
        assert isinstance(report["managed_capabilities"], list)
        assert periodic_report["report_scope"] == "periodic"


@pytest.mark.asyncio
async def test_skill_runtime_extracts_token_usage_from_stream_events():
    class StreamSkill(BaseSkill):
        skill_name = "lead.test.stream"

        def execute(self, input_data):
            return {"ok": True}

        async def execute_stream(self, input_data):
            yield {"type": "progress", "progress": 0.5, "message": "halfway"}
            yield {
                "type": "result",
                "data": {
                    "summary": "done",
                    "token_usage": {"input_tokens": 3, "output_tokens": 5, "total_tokens": 8},
                },
            }

    result = await SkillRuntimeManager().invoke(StreamSkill(), {"topic": "lobster"}, method_name="execute_stream")

    assert result.output_json["summary"] == "done"
    assert result.token_usage.total_tokens == 8
    assert len(result.stream_events) == 2


@pytest.mark.asyncio
async def test_workflow_engine_can_reroute_back_to_planning():
    class FakePipeline:
        def __init__(self, responses):
            self.responses = list(responses)
            self.calls = []

        async def run(self, context, input_bundle):
            self.calls.append(input_bundle)
            return self.responses.pop(0)

    class FakeWorkflowRunService:
        def __init__(self):
            self.completed = None
            self.failed = None

        async def create_run(self, **kwargs):
            return SimpleNamespace(id=1, uuid="run-qa-reroute-1")

        async def update_run_status(self, run_id, status, result_payload=None, error_message=None):
            if status == "completed":
                self.completed = {
                    "run_id": run_id,
                    "status": status,
                    "result_payload": result_payload,
                    "error_message": error_message,
                }
            if status == "failed":
                self.failed = {
                    "run_id": run_id,
                    "status": status,
                    "result_payload": result_payload,
                    "error_message": error_message,
                }
            return SimpleNamespace(id=run_id, status=status, result_payload=result_payload, error_message=error_message)

    class FakeRecorder:
        def __init__(self):
            self.statuses = []
            self.logs = []
            self.artifacts = []

        async def call_skill(self, **kwargs):
            return SimpleNamespace(raw_output=SimpleNamespace(run_plan={"route": []}, lead_route_list=[]))

        async def record_status(self, **kwargs):
            self.statuses.append(kwargs)

        async def record_log(self, **kwargs):
            self.logs.append(kwargs)

        async def record_artifact(self, **kwargs):
            self.artifacts.append(kwargs)

    request = DomainWorkflowRequest(
        domain="lobster",
        platform="douyin",
        hotspot_count=6,
        top_n=2,
        content_type="knowledge",
        style="clean",
        duration=30,
    )
    finance_result = PipelineResult(
        status="success",
        bundle={
            "finance_estimate": {"estimated_cost": 1.2},
            "finance_check": {"passed": True},
            "receipt": {"transaction_id": "tx-1"},
        },
        notes=["finance_ok"],
    )
    research_result = PipelineResult(
        status="success",
        bundle={
            "expanded_queries": ["lobster"],
            "selected_hotspots": [{"uuid": "hotspot-1"}],
            "bundle": {"selected_hotspots": [{"uuid": "hotspot-1"}]},
        },
        notes=["research_ok"],
    )
    analysis_result = PipelineResult(
        status="success",
        bundle={
            "analysis_reports": ["analysis-model"],
            "bundle": {"analysis_ids": ["analysis-1"]},
        },
        notes=["analysis_ok"],
    )
    initial_planning = PipelineResult(
        status="success",
        bundle={
            "prompt_package": {"script_topic": "initial topic"},
            "prompt_bundle": {"script_topic": "initial topic"},
        },
        notes=["planning_v1"],
    )
    revised_planning = PipelineResult(
        status="success",
        bundle={
            "prompt_package": {"script_topic": "reworked topic"},
            "prompt_bundle": {"script_topic": "reworked topic"},
        },
        notes=["planning_v2"],
    )
    initial_script = SimpleNamespace(uuid="script-1", status="pending_review")
    revised_script = SimpleNamespace(uuid="script-2", status="approved")
    initial_production = PipelineResult(
        status="success",
        bundle={
            "script": initial_script,
            "video_task": None,
            "trace_bundle": {
                "render_bundle": {
                    "delivery_asset_url": "/media/videos/initial.mp4",
                    "render_mode": "preview_placeholder",
                }
            },
            "bundle": {
                "script": initial_script,
                "video_task": None,
                "render_bundle": {"delivery_asset_url": "/media/videos/initial.mp4"},
            },
        },
        notes=["production_v1"],
    )
    revised_production = PipelineResult(
        status="success",
        bundle={
            "script": revised_script,
            "video_task": None,
            "trace_bundle": {
                "render_bundle": {
                    "delivery_asset_url": "/media/videos/reworked.mp4",
                    "render_mode": "preview_placeholder",
                }
            },
            "bundle": {
                "script": revised_script,
                "video_task": None,
                "render_bundle": {"delivery_asset_url": "/media/videos/reworked.mp4"},
            },
        },
        notes=["production_v2"],
    )
    failed_qa_report = {
        "pass": False,
        "qa_status": "failed",
        "failed_dimensions": ["gene_alignment"],
        "recommendation": "Planning needs revision.",
    }
    failed_qa = PipelineResult(
        status="rework",
        bundle={"qa_report": failed_qa_report, "bundle": {"qa_report": failed_qa_report, "checks": []}},
        notes=["qa_failed"],
    )
    passed_qa_report = {
        "pass": True,
        "qa_status": "passed",
        "failed_dimensions": [],
        "recommendation": "Approved.",
    }
    passed_qa = PipelineResult(
        status="success",
        bundle={"qa_report": passed_qa_report, "bundle": {"qa_report": passed_qa_report, "checks": []}},
        notes=["qa_passed"],
    )
    publish_result = PipelineResult(
        status="success",
        bundle={"bundle": {"publish_result": {"status": "published"}}},
        notes=["publish_ok"],
    )

    planning_pipeline = FakePipeline([initial_planning, revised_planning])
    production_pipeline = FakePipeline([initial_production, revised_production])
    qa_pipeline = FakePipeline([failed_qa, passed_qa])
    recorder = FakeRecorder()
    workflow_run_service = FakeWorkflowRunService()
    assembly = SimpleNamespace(
        control_plane=SimpleNamespace(get_qa_rework_policy=lambda: {"max_attempts": 1}),
        workflow_run_service=workflow_run_service,
        finance_pipeline=FakePipeline([finance_result]),
        research_pipeline=FakePipeline([research_result]),
        analysis_pipeline=FakePipeline([analysis_result]),
        planning_pipeline=planning_pipeline,
        production_pipeline=production_pipeline,
        qa_pipeline=qa_pipeline,
        publish_pipeline=FakePipeline([publish_result]),
        qa_reroute_service=QARerouteService(
            SimpleNamespace(
                get_qa_reroute_policy=lambda: {
                    "strategy": "conservative",
                    "mapping": {
                        "passed": "lead.publish",
                        "retry_production": "lead.production",
                        "retry_research_development": "lead.research_development",
                    },
                }
            )
        ),
        get_skill=lambda name: object(),
    )

    result = await WorkflowExecutionEngine(assembly, recorder=recorder).run_domain_workflow(request)

    assert len(planning_pipeline.calls) == 2
    assert len(production_pipeline.calls) == 2
    assert len(qa_pipeline.calls) == 2
    assert production_pipeline.calls[1]["planning_bundle"]["prompt_package"]["script_topic"] == "reworked topic"
    assert result["prompt_package"]["script_topic"] == "reworked topic"
    assert result["script_id"] == "script-2"
    assert result["qa_status"] == "passed"
    assert workflow_run_service.failed is None
    assert any(log["message"] == "QA requested reroute" for log in recorder.logs)


@pytest.mark.asyncio
async def test_workflow_run_service_persists_trigger_id(session):
    service = WorkflowRunService(session)

    run = await service.create_run(
        trace_id="trace-trigger-1",
        workflow_type="domain_auto_run",
        domain="lobster",
        platform="douyin",
        input_params={"top_n": 2},
        trigger_id="trigger-uuid-1",
    )
    await session.commit()

    assert run.trigger_id == "trigger-uuid-1"
    assert run.result_payload["top_n"] == 2


@pytest.mark.asyncio
async def test_trigger_scanner_skips_when_active_run_exists(session):
    class FakeEngine:
        async def run_domain_workflow(self, **kwargs):
            raise AssertionError("workflow should not run when duplicate active run exists")

    trigger = WorkflowTrigger(
        name="daily-lobster",
        cron="0 3 * * *",
        domain="lobster",
        platform="douyin",
        input_params={"top_n": 2},
        enabled=True,
    )
    session.add(trigger)
    await session.flush()

    session.add(
        WorkflowRun(
            trace_id="trace-dup-1",
            workflow_type="domain_auto_run",
            domain="lobster",
            platform="douyin",
            status="running",
            trigger_id=trigger.uuid,
        )
    )
    await session.flush()

    scanner = TriggerScanner(FakeEngine())
    await scanner._fire_trigger(trigger, session)

    assert trigger.last_fired_at is None


@pytest.mark.asyncio
async def test_trigger_scanner_passes_trigger_uuid_to_workflow_engine(session):
    class FakeEngine:
        def __init__(self):
            self.calls = []

        async def run_domain_workflow(self, request, **kwargs):
            self.calls.append({"request": request, **kwargs})
            return {"status": "completed"}

    trigger = WorkflowTrigger(
        name="daily-lobster",
        cron="0 3 * * *",
        domain="lobster",
        platform="douyin",
        input_params={"top_n": 2},
        enabled=True,
    )
    session.add(trigger)
    await session.flush()

    engine = FakeEngine()
    scanner = TriggerScanner(engine)
    await scanner._execute_workflow(trigger)

    assert len(engine.calls) == 1
    assert engine.calls[0]["request"].domain == "lobster"
    assert engine.calls[0]["request"].top_n == 2
    assert engine.calls[0]["trigger_id"] == trigger.uuid
