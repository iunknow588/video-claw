from pathlib import Path

import pytest

from departments.CSO.services.material_reference import MaterialReferenceService
from departments.COO.services.composition import RenderExecutionService
from departments.CIO.services.storage import build_placeholder_video_bytes
from departments.COO.services.asset_management import SubtitleComposerService
from departments.COO.services.asset_management import VoiceoverService
from departments.COO.services.composition import VideoCompositionService
from departments.CHO.agent import CHOAgent
from departments.CHO.services import CHOService
from departments.CCO.agent import AnalysisAgent
from departments.COO.agent import ProductionAgent
from departments.CSO.agent import ResearchAgent
from departments.CMO.skills.chat_ui import ChatUISkill
from departments.CSO.skills.domain_query_expansion import DomainQueryExpansionSkill
from departments.CQO.skills import DeliveryAssetCheckSkill, RenderOutputCheckSkill
from departments.CEO.skills.registry import ensure_builtin_skills_registered, registry


def test_subtitle_composer_creates_srt_file(tmp_path, monkeypatch):
    from departments.CEO.core.config import settings

    monkeypatch.setattr(settings.storage, "media_root", str(tmp_path))
    service = SubtitleComposerService()

    result = service.compose(
        trace_id="trace-subtitle-1",
        target_duration=18,
        script={
            "title": "Lobster ops",
            "duration": 18,
            "scenes": [
                {"timing": "0-6s", "text": "First explain the customer problem."},
                {"timing": "6-12s", "audio": "Then show the workflow fix."},
                {"timing": "12-18s", "text": "Close with a clear CTA."},
            ],
        },
    )

    assert result["subtitle_file"].endswith("trace-subtitle-1.srt")
    assert len(result["subtitle_items"]) == 3
    assert "00:00:00,000 --> 00:00:06,000" in result["subtitle_text"]
    assert (tmp_path / "subtitles" / "trace-subtitle-1.srt").exists()


def test_material_reference_service_builds_candidates_and_scene_map(tmp_path, monkeypatch):
    from departments.CEO.core.config import settings

    monkeypatch.setattr(settings.storage, "media_root", str(tmp_path))
    service = MaterialReferenceService()

    result = service.plan(
        search_terms=["lobster kitchen", "night storefront"],
        scenes=[
            {"timing": "0-5s", "visuals": "lobster kitchen prep close-up"},
            {"timing": "5-10s", "visuals": "night storefront traffic"},
        ],
        platform="douyin",
        target_duration=10,
    )

    assert result["platform"] == "douyin"
    assert len(result["material_candidates"]) >= 2
    assert len(result["scene_material_map"]) == 2
    assert result["scene_material_map"][0]["candidate_id"] is not None
    assert "material_cache" in result["material_candidates"][0]["cache_path"]


def test_voiceover_service_creates_audio_and_ssml(tmp_path, monkeypatch):
    from departments.CEO.core.config import settings

    monkeypatch.setattr(settings.storage, "media_root", str(tmp_path))
    service = VoiceoverService()

    result = service.generate(
        trace_id="trace-voice-1",
        target_duration=12,
        script={
            "duration": 12,
            "scenes": [
                {"timing": "0-6s", "audio": "Explain the first workflow problem."},
                {"timing": "6-12s", "audio": "Then present the operating fix."},
            ],
        },
    )

    assert result["audio_file"].endswith("trace-voice-1.wav")
    assert result["provider"] == "placeholder_tts"
    assert "<speak" in result["ssml"]
    assert len(result["voice_segments"]) == 2
    assert (tmp_path / "audio" / "trace-voice-1.wav").exists()


def test_video_composition_service_builds_ffmpeg_friendly_plan():
    service = VideoCompositionService()
    result = service.build_plan(
        platform="douyin",
        script={
            "scenes": [
                {"timing": "0-5s", "visuals": "lobster kitchen", "text": "Hook"},
                {"timing": "5-10s", "visuals": "storefront", "text": "CTA"},
            ]
        },
        material_bundle={
            "scene_material_map": [
                {"candidate_id": "candidate-1", "cache_path": "cache/a.mp4"},
                {"candidate_id": "candidate-2", "cache_path": "cache/b.mp4"},
            ],
            "material_candidates": [
                {"candidate_id": "candidate-1", "cache_path": "cache/a.mp4"},
                {"candidate_id": "candidate-2", "cache_path": "cache/b.mp4"},
            ],
        },
        subtitle_bundle={"subtitle_file": "media/subtitles/demo.srt", "subtitle_items": [{"text": "Hook"}, {"text": "CTA"}]},
        voiceover_bundle={"audio_file": "media/audio/demo.wav", "voice_profile": "neutral", "voice_segments": [{"text": "Hook"}, {"text": "CTA"}]},
        video_task=None,
    )

    assert result["render_preset"]["resolution"] == "1080x1920"
    assert len(result["scene_clips"]) == 2
    assert "subtitles" in result["ffmpeg_plan"]["filters"]
    assert "media/audio/demo.wav" in result["ffmpeg_plan"]["inputs"]


def test_delivery_asset_check_passes_when_assets_are_complete(tmp_path):
    subtitle_path = tmp_path / "demo.srt"
    audio_path = tmp_path / "demo.wav"
    material_path_a = tmp_path / "scene-a.mp4"
    material_path_b = tmp_path / "scene-b.mp4"
    subtitle_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nDemo\n", encoding="utf-8")
    audio_path.write_bytes(b"wav-demo")
    material_path_a.write_bytes(b"mp4-a")
    material_path_b.write_bytes(b"mp4-b")

    result = DeliveryAssetCheckSkill().execute(
        {
            "script": {
                "scenes": [
                    {"timing": "0-5s", "text": "Hook"},
                    {"timing": "5-10s", "text": "CTA"},
                ]
            },
            "material_bundle": {
                "scene_material_map": [
                    {"candidate_id": "candidate-1", "cache_path": str(material_path_a)},
                    {"candidate_id": "candidate-2", "cache_path": str(material_path_b)},
                ]
            },
            "subtitle_bundle": {
                "subtitle_file": str(subtitle_path),
                "subtitle_items": [{"text": "Hook"}, {"text": "CTA"}],
            },
            "voiceover_bundle": {
                "audio_file": str(audio_path),
                "voice_segments": [{"text": "Hook"}, {"text": "CTA"}],
            },
            "composition_bundle": {
                "ffmpeg_plan": {
                    "inputs": [str(subtitle_path), str(audio_path)],
                }
            },
        }
    )

    assert result["pass"] is True
    assert result["dimension"] == "delivery_asset"


def test_placeholder_video_bytes_uses_ffmpeg_path_when_available(monkeypatch):
    expected = b"fake-mp4-bytes"

    def fake_run(command, check, stdout, stderr):
        output_path = Path(command[-1])
        output_path.write_bytes(expected)
        return None

    monkeypatch.setattr("departments.CIO.services.storage.shutil.which", lambda name: "ffmpeg" if name == "ffmpeg" else None)
    monkeypatch.setattr("departments.CIO.services.storage.subprocess.run", fake_run)

    result = build_placeholder_video_bytes("task-ffmpeg")

    assert result == expected


@pytest.mark.asyncio
async def test_render_execution_service_builds_preview_asset(tmp_path, monkeypatch):
    from departments.CEO.core.config import settings

    monkeypatch.setattr(settings.storage, "media_root", str(tmp_path))
    monkeypatch.setattr(settings.storage, "media_url_prefix", "/media")
    service = RenderExecutionService()

    result = await service.execute(
        trace_id="trace-render-1",
        platform="douyin",
        duration=10,
        composition_bundle={
            "scene_clips": [
                {
                    "timing": "0-5s",
                    "text_overlay": "Hook",
                    "voice_segment": {"start": 0, "end": 5},
                    "material_candidate": {"cache_path": str(tmp_path / "material-cache-a.mp4"), "duration_hint": 5},
                },
                {
                    "timing": "5-10s",
                    "text_overlay": "CTA",
                    "voice_segment": {"start": 5, "end": 10},
                    "material_candidate": {"cache_path": str(tmp_path / "material-cache-b.mp4"), "duration_hint": 5},
                },
            ],
            "render_preset": {"resolution": "1080x1920", "fps": 30},
            "ffmpeg_plan": {"inputs": ["audio.wav", "subtitle.srt"], "filters": ["subtitles", "amix"]},
        },
        video_task=None,
    )

    assert result["render_mode"] in {"preview_placeholder", "ffmpeg_preview"}
    assert result["delivery_asset_url"].startswith("/media/videos/render-trace-render-1")
    assert Path(result["render_manifest_path"]).exists()
    assert result["scene_clip_count"] == 2
    if result["render_mode"] == "ffmpeg_preview":
        assert result["local_render_path"] is not None
        assert Path(result["local_render_path"]).exists()
        assert result["materialized_clip_count"] == 2


def test_render_output_check_passes_for_local_asset(tmp_path, monkeypatch):
    from departments.CEO.core.config import settings

    media_root = tmp_path / "media"
    video_dir = media_root / "videos"
    video_dir.mkdir(parents=True)
    asset_path = video_dir / "render-test.mp4"
    asset_path.write_bytes(b"mp4-demo")
    manifest_path = tmp_path / "render.json"
    manifest_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(settings.storage, "media_root", str(media_root))
    monkeypatch.setattr(settings.storage, "media_url_prefix", "/media")

    result = RenderOutputCheckSkill().execute(
        {
            "platform": "douyin",
            "render_bundle": {
                "delivery_asset_url": "/media/videos/render-test.mp4",
                "render_manifest_path": str(manifest_path),
                "render_mode": "passthrough_video_task",
                "input_count": 2,
            },
        }
    )

    assert result["pass"] is True
    assert result["dimension"] == "render_output"


def test_skill_catalog_exposes_new_moneyprinter_style_adaptations():
    ensure_builtin_skills_registered()

    material_descriptor = registry.get_descriptor("lead.research.material_search")
    subtitle_descriptor = registry.get_descriptor("lead.production.subtitle_compose")
    voice_descriptor = registry.get_descriptor("lead.production.voiceover_generate")
    compose_descriptor = registry.get_descriptor("lead.production.video_compose_plan")
    delivery_descriptor = registry.get_descriptor("lead.qa.delivery_asset_check")
    render_descriptor = registry.get_descriptor("lead.production.render_execute")
    render_check_descriptor = registry.get_descriptor("lead.qa.render_output_check")

    assert "material" in material_descriptor.tags
    assert "planning" in material_descriptor.tags
    assert "subtitle" in subtitle_descriptor.tags
    assert "script" in subtitle_descriptor.parameters_schema["properties"]
    assert "voiceover" in voice_descriptor.tags
    assert "compose" in compose_descriptor.tags
    assert "delivery" in delivery_descriptor.tags
    assert "render" in render_descriptor.tags
    assert "render" in render_check_descriptor.tags


def test_chat_ui_default_prompt_example_includes_video_type_and_platform():
    skill = ChatUISkill()

    empty_result = skill.execute({"action": "interpret_user_message", "message": ""})
    help_result = skill.execute({"action": "interpret_user_message", "message": "你好"})

    assert "知识讲解视频" in empty_result["reply_message"]
    assert "小红书" in empty_result["reply_message"]
    assert "知识讲解视频" in help_result["reply_message"]
    assert "小红书" in help_result["reply_message"]


def test_canonical_department_packages_expose_agents_and_skill_groups():
    assert CHOAgent.department_domain == "public_agent_management"
    assert ResearchAgent.department_domain == "research"
    assert AnalysisAgent.department_domain == "analysis"
    assert ProductionAgent.department_domain == "production"

    cho_skill_names = {skill.__name__ for skill in CHOAgent.managed_skill_classes}
    research_skill_names = {skill.__name__ for skill in ResearchAgent.managed_skill_classes}
    analysis_skill_names = {skill.__name__ for skill in AnalysisAgent.managed_skill_classes}
    production_skill_names = {skill.__name__ for skill in ProductionAgent.managed_skill_classes}

    assert "PublicAgentRegistrySkill" in cho_skill_names
    assert "MaterialSearchSkill" in research_skill_names
    assert "AnalysisPersistSkill" in analysis_skill_names
    assert "RenderExecuteSkill" in production_skill_names


def test_cho_service_exposes_department_level_agent_governance_use_cases():
    service = CHOService()

    roster = service.list_public_agents()
    assert roster["count"] >= 1
    assert any(item["agent_name"] == "CMOAgent" for item in roster["public_agents"])

    provisioned = service.provision_agent(
        {
            "agent_name": "DemoAgent",
            "entrypoint": "app.demo.agent.DemoAgent",
            "domain": "demo",
            "scope": "shared_support",
            "owner_leader": "lead.cho",
            "capabilities": ["demo_capability"],
        }
    )
    assert provisioned["agent_name"] == "DemoAgent"

    profile = service.update_capabilities("DemoAgent", ["demo_capability", "reporting"])
    assert profile["capabilities"] == ["demo_capability", "reporting"]

    described = service.describe_agent("DemoAgent")
    assert described["found"] is True
    assert described["capability_profile"]["integration_type"] == "demo"

    health = service.check_health()
    demo_health = next(item for item in health["health_items"] if item["agent_name"] == "DemoAgent")
    assert demo_health["availability"] == "ready"
    assert demo_health["governance_status"] == "managed"

    service.decommission_agent("DemoAgent")
    decommissioned = service.agent_management.get_public_agent("DemoAgent")
    assert decommissioned["lifecycle_status"] == "decommissioned"


def test_cho_agent_exposes_service_layer():
    assert CHOAgent.service_class is CHOService
