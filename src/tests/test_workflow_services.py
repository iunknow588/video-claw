import pytest

from app.core.config import settings
from app.models.analysis import AnalysisReport
from app.models.cost import CostRecord
from app.models.hotspot import HotspotItem
from app.models.review import ReviewRecord
from app.models.script import Script
from app.services.ai_clients import AIProviderResult, TokenUsage
from app.services.analysis import AIAnalysisService
from app.services.cio import CIOInformationService
from app.services.hotspot import HotspotService
from app.services.operations import OperationsService
from app.services.script import ScriptService
from app.services.storage import (
    LocalVideoStorage,
    S3CompatibleVideoStorage,
    describe_video_storage,
    get_video_storage,
)
from app.services.video import VideoService
from app.schemas.video import HotspotCreate


@pytest.mark.asyncio
async def test_hotspot_search_and_fetch(session):
    service = HotspotService(session)
    await service.create(
        HotspotCreate(
            platform="bilibili",
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
    monkeypatch.setattr(settings, "AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED", False)

    async def fake_chat_json(*, model: str, prompt: str):
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
async def test_local_video_storage_returns_media_url(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "MEDIA_URL_PREFIX", "/media")
    monkeypatch.setattr(settings, "MEDIA_BASE_URL", None)

    storage = LocalVideoStorage()
    url = await storage.save_video(task_uuid="task-001", content=b"demo-bytes")

    assert url == "/media/videos/task-001.mp4"
    assert (tmp_path / "videos" / "task-001.mp4").exists()


@pytest.mark.asyncio
async def test_local_video_storage_prefers_media_base_url(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "MEDIA_URL_PREFIX", "/media")
    monkeypatch.setattr(settings, "MEDIA_BASE_URL", "https://cdn.example.com/media")

    storage = LocalVideoStorage()
    url = await storage.save_video(task_uuid="task-002", content=b"demo-bytes")

    assert url == "https://cdn.example.com/media/videos/task-002.mp4"


def test_storage_factory_supports_s3_backend(monkeypatch):
    monkeypatch.setattr(settings, "VIDEO_STORAGE_BACKEND", "s3_compatible")
    storage = get_video_storage()
    assert isinstance(storage, S3CompatibleVideoStorage)


def test_describe_video_storage_for_s3_backend(monkeypatch):
    monkeypatch.setattr(settings, "VIDEO_STORAGE_BACKEND", "s3_compatible")
    monkeypatch.setattr(settings, "MEDIA_URL_PREFIX", "/media")
    monkeypatch.setattr(settings, "S3_BUCKET", "lobster-videos")
    monkeypatch.setattr(settings, "S3_ACCESS_KEY_ID", "demo-ak")
    monkeypatch.setattr(settings, "S3_SECRET_ACCESS_KEY", "demo-sk")
    monkeypatch.setattr(settings, "S3_ENDPOINT_URL", "https://s3.example.com")
    monkeypatch.setattr(settings, "S3_REGION", "ap-east-1")
    monkeypatch.setattr(settings, "S3_OBJECT_PREFIX", "videos")
    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "https://cdn.example.com/videos")

    result = describe_video_storage()

    assert result["backend"] == "s3_compatible"
    assert result["configured"] is True
    assert result["bucket"] == "lobster-videos"
    assert result["public_base_url"] == "https://cdn.example.com/videos"
