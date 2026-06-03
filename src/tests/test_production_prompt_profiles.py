from departments.CIO.models.analysis import AnalysisReport
from departments.CIO.models.script import Script
from departments.COO.services.script_management import ScriptService
from departments.COO.services.video_production import VideoService


def test_script_prompt_includes_content_type_audience_and_goal(session):
    service = ScriptService(session)
    analysis = AnalysisReport(
        hotspot_id="hotspot-1",
        analysis_type="comprehensive",
        framework_summary="Hook -> explanation -> CTA",
        reusable_elements=["contrast", "countdown"],
    )

    prompt = service._build_script_prompt(
        analysis,
        "review",
        "fast",
        "龙虾半成品",
        30,
        audience="餐饮老板",
        publish_goal="提升到店转化",
    )

    assert "测评对比类" in prompt
    assert "快节奏" in prompt
    assert "餐饮老板" in prompt
    assert "提升到店转化" in prompt
    assert "comparison dimensions" in prompt


def test_video_prompt_includes_platform_and_content_type_guidance(session):
    service = VideoService(session)
    script = Script(
        analysis_id="analysis-1",
        content_type="story",
        style="story",
        title="夜宵门店冲突",
        topic="夜宵门店冲突",
        duration=45,
        hook="冲突开场",
        scenes=[
            {"visuals": "顾客与店员对峙"},
            {"visuals": "反转和解"},
        ],
        status="approved",
        version=1,
    )

    prompt = service._build_video_prompt(script, "cinematic", platform="bilibili")

    assert "B站" in prompt
    assert "剧情演绎类" in prompt
    assert "电影感" in prompt
    assert "cinematic framing" in prompt
