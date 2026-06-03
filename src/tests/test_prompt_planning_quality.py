from types import SimpleNamespace

import pytest

from departments.CIO.models.analysis import AnalysisReport
from departments.CIO.models.hotspot import HotspotItem
from departments.CSO.services.trend_intelligence import TrendIntelligenceService
from departments.CIO.schemas.video import DomainWorkflowRequest
from departments.CTO.skills.prompt_validation import PromptValidationSkill
from departments.CTO.skills.prompt_version import PromptVersionSkill
from departments.CTO.skills.prompt_package import PromptPackageSkill
from departments.CTO.skills.title_candidate import TitleCandidateSkill
from departments.CTO.services.use_cases.prompt_planning import PromptPlanningUseCase


def test_trend_prompt_package_filters_noise_and_includes_platform_duration():
    service = TrendIntelligenceService()
    hotspot = HotspotItem(
        uuid="hotspot-1",
        platform="xiaohongshu",
        content_id="content-1",
        title="The best lobster store operations guide for growth",
        author="operator",
        category="business",
        tags=["lobster", "operations", "growth"],
    )
    analysis = AnalysisReport(
        hotspot_id="hotspot-1",
        analysis_type="comprehensive",
        framework_summary="Hook first, then three practical steps.",
        reusable_elements=["contrast", "numbers", "practical example"],
        risk_warnings=["avoid generic intro"],
    )

    package = service.build_prompt_package(
        domain="lobster store operations",
        hotspots=[hotspot],
        analyses=[analysis],
        platform="xiaohongshu",
        duration=35,
        style="clean",
        content_type="review",
        audience="restaurant owners",
        publish_goal="increase store visits",
    )

    normalized_keywords = [item.lower() for item in package["core_keywords"]]
    assert "the" not in normalized_keywords
    assert "for" not in normalized_keywords
    assert "\u5e73\u53f0\uff1a\u5c0f\u7ea2\u4e66" in package["video_prompt"]
    assert "\u65f6\u957f\uff1a35\u79d2" in package["video_prompt"]
    assert "\u7c7b\u578b\uff1a\u6d4b\u8bc4\u5bf9\u6bd4\u7c7b" in package["video_prompt"]


def test_prompt_validation_and_version_skills_attach_quality_metadata():
    prompt_bundle = {
        "trace_id": "trace-1",
        "prompt_summary": "Generate a practical prompt package for restaurant operators.",
        "script_topic": "Three ways to improve lobster store operations",
        "video_prompt": (
            "\u4e3b\u9898\uff1alobster store operations\uff1b\u5e73\u53f0\uff1a\u5c0f\u7ea2\u4e66\uff1b"
            "\u65f6\u957f\uff1a35\u79d2\uff1b\u7c7b\u578b\uff1a\u6d4b\u8bc4\u5bf9\u6bd4\u7c7b\uff1b"
            "\u89c6\u89c9\u98ce\u683c\uff1a\u4e13\u4e1a\u5e72\u51c0\u98ce\u683c\u3002"
        ),
        "core_keywords": ["lobster", "operations", "growth"],
        "hook_keywords": ["growth", "operations"],
        "title_candidates": [
            "Three ways to improve lobster store operations",
            "How lobster stores increase repeat visits",
            "A practical comparison for store operators",
        ],
        "script_topic_variants": [
            "Three ways to improve lobster store operations",
            "How lobster stores increase repeat visits",
            "A practical comparison for store operators",
        ],
        "video_prompt_variants": [
            "variant one",
            "variant two",
        ],
        "image_prompt_variants": [
            "cover variant one",
            "cover variant two",
        ],
    }

    validation = PromptValidationSkill().run(prompt_bundle)
    version = PromptVersionSkill().run(validation)

    assert validation["passed"] is True
    assert validation["quality_score"] >= 0.8
    assert validation["issues"] == []
    assert version["version"] == 1
    assert version["version_label"].startswith("prompt:v1:")
    assert len(version["fingerprint"]) == 12


@pytest.mark.asyncio
async def test_domain_workflow_prompt_package_includes_quality_metadata(api_client):
    response = await api_client.post(
        "/api/cao/workflows/runs",
        json={
            "domain": "lobster store operations",
            "platform": "xiaohongshu",
            "hotspot_count": 9,
            "top_n": 3,
            "content_type": "review",
            "style": "clean",
            "duration": 35,
            "auto_approve_script": False,
            "auto_generate_video": False,
            "publish_goal": "increase store visits",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["prompt_package"]["version"] == 1
    assert data["prompt_package"]["version_label"].startswith("prompt:v1:")
    assert data["prompt_package"]["quality_score"] >= 0.8
    assert "\u5e73\u53f0\uff1a\u5c0f\u7ea2\u4e66" in data["prompt_package"]["video_prompt"]
    assert "\u65f6\u957f\uff1a35\u79d2" in data["prompt_package"]["video_prompt"]


@pytest.mark.asyncio
async def test_prompt_planning_use_case_rejects_invalid_prompt_bundle():
    class FakeRecorder:
        async def call_skill(self, *, skill, input_bundle, **kwargs):
            return SimpleNamespace(output_json=skill.run(input_bundle))

    class FakeTrendService:
        def build_prompt_package(self, **kwargs):
            return {
                "prompt_summary": "",
                "script_topic": "",
                "video_prompt": "",
                "core_keywords": [],
                "hook_keywords": [],
                "title_candidates": [],
                "script_topic_variants": [],
                "video_prompt_variants": [],
                "image_prompt_variants": [],
            }

    skills = {
        "lead.research_development.prompt_package": PromptPackageSkill(),
        "lead.research_development.title_candidate": TitleCandidateSkill(),
        "lead.research_development.prompt_validation": PromptValidationSkill(),
        "lead.research_development.prompt_version": PromptVersionSkill(),
    }
    assembly = SimpleNamespace(
        trend_service=FakeTrendService(),
        recorder=FakeRecorder(),
        get_skill=lambda name: skills[name],
        load_hotspot_sync=lambda item: item,
    )
    request = DomainWorkflowRequest(
        domain="lobster store operations",
        platform="xiaohongshu",
        content_type="review",
        style="clean",
        duration=35,
    )

    with pytest.raises(ValueError, match="Prompt validation failed"):
        await PromptPlanningUseCase(assembly).execute(
            trace_id="trace-2",
            request=request,
            domain=request.domain,
            hotspots=[],
            analyses=[],
        )
