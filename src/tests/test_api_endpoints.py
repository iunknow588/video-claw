import json

import pytest

from departments.CEO.core.config import settings
from departments.CEO.services.orchestration.domain_workflow import DomainWorkflowService
from departments.CIO.schemas.video import DomainWorkflowRequest
from departments.CIO.services.workflow_runs import WorkflowRunService
from departments.CQO.skills.qa_report import QAReportSkill


@pytest.mark.asyncio
async def test_full_api_workflow(api_client):
    fetch_resp = await api_client.post(
        "/api/hotspots/fetch",
        json={
            "platform": "douyin",
            "keyword": "lobster",
            "count": 2,
        },
    )
    assert fetch_resp.status_code == 200
    hotspots = fetch_resp.json()
    assert len(hotspots) >= 1
    assert hotspots[0]["source_mode"] == "mock"
    assert hotspots[0]["url"].startswith("https://example.com/")
    assert "mvp" in hotspots[0]["tags"]
    hotspot_id = hotspots[0]["uuid"]

    analysis_resp = await api_client.post(
        "/api/analysis",
        json={"hotspot_id": hotspot_id, "analysis_type": "comprehensive"},
    )
    assert analysis_resp.status_code == 200
    analysis = analysis_resp.json()
    analysis_id = analysis["uuid"]
    assert analysis["report_title"] == "爆款DNA报告"
    assert "dna_report" in analysis
    assert "framework_summary" in analysis["dna_report"]

    script_resp = await api_client.post(
        "/api/scripts",
        json={
            "analysis_id": analysis_id,
            "content_type": "knowledge",
            "style": "clean",
            "topic": "Lobster workflow",
            "duration": 60,
        },
    )
    assert script_resp.status_code == 200
    script = script_resp.json()
    script_id = script["uuid"]
    assert script["status"] == "pending_review"
    assert script["hook"]
    assert script["cta"]
    assert len(script["scenes"]) >= 1
    assert "script_bundle" in script

    approve_script_resp = await api_client.post(
        f"/api/scripts/review/{script_id}",
        json={"approved": True, "feedback": "ok"},
    )
    assert approve_script_resp.status_code == 200
    approved_script = approve_script_resp.json()
    assert approved_script["status"] == "approved"
    assert len(approved_script["scenes"]) >= 1

    video_resp = await api_client.post(
        "/api/videos",
        json={
            "script_id": script_id,
            "style": "realistic",
            "size": "1080x1920",
        },
    )
    assert video_resp.status_code == 200
    video_task = video_resp.json()
    task_id = video_task["uuid"]

    task_status_resp = await api_client.get(f"/api/videos/task/{task_id}")
    assert task_status_resp.status_code == 200

    storage_resp = await api_client.get("/api/operations/storage")
    assert storage_resp.status_code == 200
    assert "backend" in storage_resp.json()

    summary_resp = await api_client.get("/api/operations/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["counts"]["hotspots"] >= 1


@pytest.mark.asyncio
async def test_video_requires_approved_script(api_client):
    fetch_resp = await api_client.post(
        "/api/hotspots/fetch",
        json={
            "platform": "xigua",
            "keyword": "ops",
            "count": 1,
        },
    )
    hotspot_id = fetch_resp.json()[0]["uuid"]

    analysis_resp = await api_client.post(
        "/api/analysis",
        json={"hotspot_id": hotspot_id, "analysis_type": "comprehensive"},
    )
    analysis_id = analysis_resp.json()["uuid"]

    script_resp = await api_client.post(
        "/api/scripts",
        json={
            "analysis_id": analysis_id,
            "content_type": "knowledge",
            "style": "fast",
            "topic": "Ops workflow",
            "duration": 30,
        },
    )
    script_id = script_resp.json()["uuid"]

    video_resp = await api_client.post(
        "/api/videos",
        json={
            "script_id": script_id,
            "style": "realistic",
            "size": "1080x1920",
        },
    )
    assert video_resp.status_code == 400
    assert video_resp.json()["detail"] == "Script not approved"


@pytest.mark.asyncio
async def test_image_task_endpoint_returns_placeholder_asset(api_client):
    response = await api_client.post(
        "/api/images",
        json={
            "prompt": "龙虾门店运营封面图，强对比画面，适合抖音竖屏首帧",
            "negative_prompt": "模糊, 低清晰度",
            "aspect_ratio": "9:16",
            "resolution": "2k",
            "image_count": 1,
            "use_case": "cover",
        },
    )
    assert response.status_code == 200
    task = response.json()
    assert task["status"] in {"pending", "processing", "completed"}

    status_resp = await api_client.get(f"/api/images/task/{task['uuid']}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["provider_name"] == "hidream"

    list_resp = await api_client.get("/api/images")
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert any(item["uuid"] == task["uuid"] for item in listed)


@pytest.mark.asyncio
async def test_domain_workflow_returns_prompt_package(api_client):
    response = await api_client.post(
        "/api/cao/workflows/runs",
        json={
            "domain": "龙虾餐饮",
            "platform": "douyin",
            "hotspot_count": 9,
            "top_n": 3,
            "content_type": "knowledge",
            "style": "clean",
            "duration": 30,
            "auto_approve_script": False,
            "auto_generate_video": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "龙虾餐饮"
    assert len(data["expanded_queries"]) >= 3
    assert len(data["selected_hotspots"]) == 3
    assert len(data["prompt_package"]["core_keywords"]) >= 1
    assert len(data["prompt_package"]["script_topic_variants"]) >= 3
    assert len(data["prompt_package"]["video_prompt_variants"]) >= 2
    assert len(data["prompt_package"]["image_prompt_variants"]) >= 2
    assert data["workflow_run_id"] is not None
    assert data["script_status"] == "pending_review"
    assert data["qa_status"] == "passed"
    assert data["qa_bundle"]["qa_report"]["pass"] is True
    assert data["video_task_id"] is None
    assert data["video_url"] is not None
    assert data["production_bundle"]["material_bundle"]["material_candidates"]
    assert data["production_bundle"]["subtitle_bundle"]["subtitle_file"].endswith(".srt")
    assert data["production_bundle"]["voiceover_bundle"]["audio_file"].endswith(".wav")
    assert data["production_bundle"]["composition_bundle"]["ffmpeg_plan"]["inputs"]
    assert data["production_bundle"]["render_bundle"]["delivery_asset_url"] == data["video_url"]
    assert data["production_bundle"]["render_bundle"]["render_mode"] in {"preview_placeholder", "ffmpeg_preview"}
    assert any(check["dimension"] == "delivery_asset" for check in data["qa_bundle"]["checks"])
    assert any(check["dimension"] == "render_output" for check in data["qa_bundle"]["checks"])


@pytest.mark.asyncio
async def test_domain_workflow_can_auto_generate_video(api_client):
    response = await api_client.post(
        "/api/cao/workflows/runs",
        json={
            "domain": "龙虾门店运营",
            "platform": "xiaohongshu",
            "hotspot_count": 8,
            "top_n": 2,
            "content_type": "knowledge",
            "style": "fast",
            "video_style": "realistic",
            "duration": 20,
            "auto_approve_script": True,
            "auto_generate_video": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["script_status"] == "approved"
    assert data["qa_status"] == "passed"
    assert data["qa_bundle"]["qa_report"]["overall_score"] > 0
    assert data["video_task_id"] is not None
    assert data["video_status"] == "completed"
    assert data["video_url"] is not None
    assert data["production_bundle"]["render_bundle"]["render_mode"] == "passthrough_video_task"


@pytest.mark.asyncio
async def test_workflow_run_history_is_queryable(api_client):
    create_resp = await api_client.post(
        "/api/cao/workflows/runs",
        json={
            "domain": "龙虾营销",
            "platform": "xigua",
            "hotspot_count": 6,
            "top_n": 2,
            "content_type": "knowledge",
            "style": "clean",
            "duration": 20,
            "auto_approve_script": False,
            "auto_generate_video": False,
        },
    )
    assert create_resp.status_code == 200
    workflow_run_id = create_resp.json()["workflow_run_id"]

    history_resp = await api_client.get("/api/cao/workflows/runs", params={"domain": "龙虾营销"})
    assert history_resp.status_code == 200
    runs = history_resp.json()
    assert len(runs) >= 1
    assert any(item["uuid"] == workflow_run_id for item in runs)


@pytest.mark.asyncio
async def test_workflow_trace_endpoint_returns_summary(api_client):
    create_resp = await api_client.post(
        "/api/cao/workflows/runs",
        json={
            "domain": "trace-summary-check",
            "platform": "douyin",
            "hotspot_count": 6,
            "top_n": 2,
            "content_type": "knowledge",
            "style": "clean",
            "duration": 20,
            "auto_approve_script": False,
            "auto_generate_video": False,
        },
    )
    assert create_resp.status_code == 200
    workflow_run_id = create_resp.json()["workflow_run_id"]

    trace_resp = await api_client.get(f"/api/cao/workflows/runs/{workflow_run_id}/trace")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()
    assert trace["run"]["uuid"] == workflow_run_id
    assert trace["summary"]["trace_id"] is not None
    assert trace["summary"]["step_count"] >= 1
    assert trace["summary"]["total_cost"] >= 0
    assert trace["summary"]["total_tokens"] > 0
    assert trace["summary"]["stage_statuses"]["lead.cfo"] in {"success", "failed"}
    assert trace["summary"]["token_usage_by_lead"]["lead.research"] > 0
    assert trace["summary"]["stage_statuses"]["lead.qa"] in {"success", "failed"}
    assert trace["summary"]["stage_statuses"]["lead.publish"] in {"success", "failed"}


@pytest.mark.asyncio
async def test_legacy_cao_run_endpoints_are_removed(api_client):
    response = await api_client.get("/api/cao/runs")
    assert response.status_code == 404

    trace_response = await api_client.get("/api/cao/runs/demo-run/trace")
    assert trace_response.status_code == 404


@pytest.mark.asyncio
async def test_workflow_skill_catalog_is_discoverable(api_client):
    response = await api_client.get("/api/cao/workflows/skills")
    assert response.status_code == 200
    skills = response.json()
    assert len(skills) >= 10
    ceo_skill = next(item for item in skills if item["name"] == "ceo.workflow")
    cfo_skill = next(item for item in skills if item["name"] == "lead.cfo.estimate_cost")
    cio_skill = next(item for item in skills if item["name"] == "lead.cio.log")
    cho_skill = next(item for item in skills if item["name"] == "lead.cho.public_agent_registry")
    promotion_skill = next(item for item in skills if item["name"] == "lead.promotion.chat_ui")
    qa_skill = next(item for item in skills if item["name"] == "lead.qa.qa_report")
    assert "planning" in ceo_skill["tags"]
    assert "governance" in ceo_skill["tags"]
    assert "platform" in ceo_skill["parameters_schema"]["properties"]
    assert "graph_definition" in ceo_skill["parameters_schema"]["properties"]
    assert "lead.cfo.estimate_cost" in ceo_skill["dependencies"]
    assert "lead.cio.log" in ceo_skill["dependencies"]
    assert "lead.cho" in ceo_skill["dependencies"]
    assert "lead.qa" in ceo_skill["dependencies"]
    assert "lead.promotion" in ceo_skill["dependencies"]
    assert "list_leaders" in ceo_skill["methods"]
    assert "set_workflow" in ceo_skill["methods"]
    assert "issue_optimize_command" in ceo_skill["methods"]
    assert "evolution_cycle" in ceo_skill["methods"]
    assert "finance" in cfo_skill["tags"]
    assert "platform" in cfo_skill["parameters_schema"]["properties"]
    assert "observability" in cio_skill["tags"]
    assert "cho" in cho_skill["tags"]
    assert "registry" in cho_skill["tags"]
    assert "promotion" in promotion_skill["tags"]
    assert "message" in promotion_skill["parameters_schema"]["properties"]
    assert "ceo.workflow" not in promotion_skill["dependencies"]
    assert "qa" in qa_skill["tags"]
    assert "checks" in qa_skill["parameters_schema"]["properties"]


@pytest.mark.asyncio
async def test_cao_console_page_is_served(api_client):
    ceo_response = await api_client.get("/ceo")
    assert ceo_response.status_code == 404

    cao_response = await api_client.get("/cao")
    assert cao_response.status_code == 200
    assert "龙虾宝宝视频制作平台" in cao_response.text
    assert "龙虾CAO 正在值班" in cao_response.text
    assert "龙虾CEO 正在默默关注视频制作流程" in cao_response.text
    assert "/api/cmo/chat" in cao_response.text
    assert "称呼设置" in cao_response.text
    assert "主链路状态" in cao_response.text
    assert "最近任务" in cao_response.text
    assert "日志记录" in cao_response.text
    assert "CEO 治理总览" not in cao_response.text


@pytest.mark.asyncio
async def test_cao_pipeline_status_hides_ceo_and_exposes_public_flow(api_client):
    response = await api_client.get("/api/cao/pipeline-status")
    assert response.status_code == 200
    data = response.json()
    assert data["console_title"] == "龙虾宝宝视频制作平台"
    assert data["console_subtitle"] == "龙虾CEO 正在默默关注视频制作流程。"
    assert data["display_policy"]["ceo_visible"] is False
    assert data["display_policy"]["workflow_visible"] is True
    assert "pipeline_metrics" in data
    assert "recent_runs" in data
    assert all(item["name"] != "ceo.workflow" for item in data["stage_statuses"] )
    stage_names = [item["name"] for item in data["stage_statuses"]]
    assert stage_names[0] == "lead.cfo"
    assert "lead.publish" in stage_names


@pytest.mark.asyncio
async def test_cao_public_trace_hides_ceo_stage(api_client):
    create_resp = await api_client.post(
        "/api/cao/workflows/runs",
        json={
            "domain": "cao-trace-check",
            "platform": "douyin",
            "hotspot_count": 6,
            "top_n": 2,
            "content_type": "knowledge",
            "style": "clean",
            "duration": 20,
            "auto_approve_script": False,
            "auto_generate_video": False,
        },
    )
    assert create_resp.status_code == 200
    workflow_run_id = create_resp.json()["workflow_run_id"]

    trace_resp = await api_client.get(f"/api/cao/workflows/runs/{workflow_run_id}/trace")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()
    assert trace["run"]["uuid"] == workflow_run_id
    assert "ceo.workflow" not in trace["summary"]["stage_statuses"]
    assert trace["public_stage_statuses"][0]["name"] == "lead.cfo"
    assert len(trace["public_steps"]) >= 1
    assert len(trace["public_logs"]) >= 3
    assert trace["public_artifacts"]["research"]["selected_hotspots"]
    assert trace["public_artifacts"]["analysis"]["reports"]
    assert trace["public_artifacts"]["analysis"]["reports"][0]["framework_summary"]
    assert trace["public_artifacts"]["planning"]["prompt_summary"]
    assert trace["public_artifacts"]["planning"]["video_prompt"]
    assert trace["public_artifacts"]["production"]["title"]
    assert trace["public_artifacts"]["production"]["scenes"]
    assert "recommendation" in trace["public_artifacts"]["qa"]
    cfo_status_logs = [item for item in trace["public_logs"] if item["type"] == "status" and item["stage"] == "lead.cfo"]
    assert cfo_status_logs
    assert any("预算校验" in item["summary"] for item in cfo_status_logs)
    assert all("lead.cfo" not in item["summary"] for item in cfo_status_logs)
    assert any(item["title"] == "已找到热门视频" for item in trace["public_logs"])
    assert any(item["title"] == "检索词已展开" for item in trace["public_logs"])
    assert any(item["title"] == "热点候选池已归档" for item in trace["public_logs"])
    assert any(item["title"] == "分析报告 1" for item in trace["public_logs"])
    assert any(item["title"] == "新提示词已生成" for item in trace["public_logs"])
    assert any(item["title"] == "提示词变体与校验结果" for item in trace["public_logs"])
    assert any(item["title"] == "素材候选已整理" for item in trace["public_logs"])
    assert any(item["title"] == "字幕与配音资产已生成" for item in trace["public_logs"])
    assert any(item["title"] == "合成与渲染计划已生成" for item in trace["public_logs"])
    assert any(item["title"] == "质检检查项明细" for item in trace["public_logs"])
    assert any(item["title"] == "技能执行：检索词扩展" for item in trace["public_logs"])
    assert any(item["title"] == "技能执行：提示词校验" for item in trace["public_logs"])
    assert any(item["title"] == "技能执行：渲染执行" for item in trace["public_logs"])
    query_skill_log = next(item for item in trace["public_logs"] if item["title"] == "技能执行：检索词扩展")
    assert any("技能标识：lead.research.domain_query_expansion" == detail for detail in query_skill_log["details"])


@pytest.mark.asyncio
async def test_cao_public_trace_exposes_failed_skill_diagnostics(api_client, session, monkeypatch):
    def fail_qa_report(self, input_data):
        raise RuntimeError("forced qa report failure")

    monkeypatch.setattr(QAReportSkill, "execute", fail_qa_report)

    service = DomainWorkflowService(session)
    request = DomainWorkflowRequest(
        domain="failure-trace-check",
        platform="douyin",
        hotspot_count=6,
        top_n=2,
        content_type="knowledge",
        style="clean",
        duration=20,
        auto_approve_script=False,
        auto_generate_video=False,
    )

    with pytest.raises(RuntimeError, match="forced qa report failure"):
        await service.run(request)

    failed_run = (await WorkflowRunService(session).list_runs(limit=1))[0]
    assert failed_run.status == "failed"

    trace_resp = await api_client.get(f"/api/cao/workflows/runs/{failed_run.uuid}/trace")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()

    assert trace["run"]["status"] == "failed"
    assert trace["summary"]["stage_statuses"]["lead.qa"] == "failed"
    assert any(item["title"] == "任务执行失败" for item in trace["public_logs"])
    assert any(item["title"] == "技能执行：质检报告生成" for item in trace["public_logs"])

    qa_skill_log = next(item for item in trace["public_logs"] if item["title"] == "技能执行：质检报告生成")
    assert "forced qa report failure" in qa_skill_log["summary"]
    assert any("执行 1 错误：forced qa report failure" == detail for detail in qa_skill_log["details"])

    failure_log = next(item for item in trace["public_logs"] if item["title"] == "任务执行失败")
    assert "forced qa report failure" in failure_log["summary"]


@pytest.mark.asyncio
async def test_cao_identity_settings_can_be_saved_and_reused(api_client):
    get_resp = await api_client.get("/api/cao/identity-settings")
    assert get_resp.status_code == 200
    settings = get_resp.json()
    assert settings["names"]["ceo"] == "龙虾CEO"
    assert settings["names"]["cao"] == "龙虾CAO"

    patch_resp = await api_client.patch(
        "/api/cao/identity-settings",
        json={"names": {"ceo": "阿甲", "cao": "小龙虾前台", "cmo": "小龙虾传播官"}},
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["names"]["ceo"] == "阿甲"
    assert updated["names"]["cao"] == "小龙虾前台"
    assert updated["names"]["cmo"] == "小龙虾传播官"

    status_resp = await api_client.get("/api/cao/pipeline-status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["console_subtitle"] == "阿甲 正在默默关注视频制作流程。"
    assert status_data["console_frontdesk_name"] == "小龙虾前台"
    assert status_data["identity_settings"]["names"]["cmo"] == "小龙虾传播官"

@pytest.mark.asyncio
async def test_cmo_chat_request_streams_status_and_result(api_client):
    response = await api_client.post(
        "/api/cmo/chat",
        json={"message": "给龙虾门店运营做一条抖音视频，30秒"},
    )
    assert response.status_code == 200

    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    event_types = [event["type"] for event in events]

    assert "reply" in event_types
    assert "status" in event_types
    assert "result" in event_types

    cfo_status_event = next(event for event in events if event["type"] == "status" and event["stage"] == "lead.cfo")
    result_event = next(event for event in events if event["type"] == "result")
    result = result_event["result"]
    assert cfo_status_event["status"] in {"running", "success"}
    assert result_event["summary"]["total_tokens"] > 0
    assert result["platform"] == "douyin"
    assert result["workflow_run_id"] is not None
    assert result["finance_bundle"]["finance_check"]["passed"] is True
    assert result["qa_status"] == "passed"
    assert result["video_task_id"] is not None
    assert result["video_url"] is not None


@pytest.mark.asyncio
async def test_cmo_chat_streams_status_and_result(api_client):
    response = await api_client.post(
        "/api/cmo/chat",
        json={"message": "给龙虾门店运营做一条抖音视频，30秒"},
    )
    assert response.status_code == 200

    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    event_types = [event["type"] for event in events]

    assert "reply" in event_types
    assert "status" in event_types
    assert "result" in event_types

    reply_event = next(event for event in events if event["type"] == "reply")
    cfo_status_event = next(event for event in events if event["type"] == "status" and event["stage"] == "lead.cfo")
    status_event = next(event for event in events if event["type"] == "status")
    qa_status_event = next(event for event in events if event["type"] == "status" and event["stage"] == "lead.qa")
    result_event = next(event for event in events if event["type"] == "result")

    assert reply_event["source"] == "lead.promotion.report_ui"
    assert cfo_status_event["source"] == "lead.promotion.progress_ui"
    assert status_event["source"] == "lead.promotion.progress_ui"
    assert qa_status_event["source"] == "lead.promotion.progress_ui"
    assert result_event["source"] == "lead.promotion.report_ui"
    assert cfo_status_event["actor_key"] == "cfo"
    assert cfo_status_event["stage_label"] == "财务闸门"
    assert "预算校验" in cfo_status_event["message"]
    assert "lead.cfo" not in cfo_status_event["message"]
    assert result_event["summary"]["total_tokens"] > 0
    assert result_event["result"]["finance_bundle"]["finance_check"]["passed"] is True
    assert result_event["result"]["qa_status"] == "passed"


@pytest.mark.asyncio
async def test_cmo_chat_can_report_recent_runs(api_client):
    create_resp = await api_client.post(
        "/api/cao/workflows/runs",
        json={
            "domain": "ceo-chat-history",
            "platform": "xigua",
            "hotspot_count": 6,
            "top_n": 2,
            "content_type": "knowledge",
            "style": "clean",
            "duration": 20,
            "auto_approve_script": False,
            "auto_generate_video": False,
        },
    )
    assert create_resp.status_code == 200

    response = await api_client.post(
        "/api/cmo/chat",
        json={"message": "查看最近任务"},
    )
    assert response.status_code == 200

    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    report_event = next(event for event in events if event["type"] == "report")
    assert len(report_event["runs"]) >= 1
    assert any(item["domain"] == "ceo-chat-history" for item in report_event["runs"])


@pytest.mark.asyncio
async def test_cao_governance_status_and_progress_endpoints(api_client):
    create_resp = await api_client.post(
        "/api/cao/workflows/runs",
        json={
            "domain": "ceo-control-check",
            "platform": "douyin",
            "hotspot_count": 6,
            "top_n": 2,
            "content_type": "knowledge",
            "style": "clean",
            "duration": 20,
            "auto_approve_script": False,
            "auto_generate_video": False,
        },
    )
    assert create_resp.status_code == 200
    workflow_run_id = create_resp.json()["workflow_run_id"]

    status_resp = await api_client.get("/api/cao/governance/company-status")
    assert status_resp.status_code == 200
    status = status_resp.json()
    assert status["mission"]
    assert status["scope"] == "company_system"
    assert "run_metrics" in status
    assert "finance_metrics" in status
    assert "information_metrics" in status
    assert "render_metrics" in status
    assert "report_center" in status
    assert len(status["report_center"]["latest_reports"]) >= 10
    assert "leader_statuses" in status
    assert status["active_leader_count"] >= 10
    assert any(item["name"] == "lead.cfo" for item in status["leader_statuses"])
    assert any(item["name"] == "lead.cio" for item in status["leader_statuses"])
    assert any(item["name"] == "lead.cho" for item in status["leader_statuses"])
    assert any(item["name"] == "lead.promotion" for item in status["leader_statuses"])
    assert "lead.promotion" in status["non_workflow_leaders"]
    assert "lead.cio" in status["non_workflow_leaders"]
    assert "lead.cho" in status["non_workflow_leaders"]
    assert "org_title_registry" in status
    assert any(item["title_code"] == "CHO" for item in status["org_title_registry"]["active_titles"])
    assert any(item["title_code"] == "CTO" for item in status["org_title_registry"]["active_titles"])
    assert any(item["title_code"] == "CMO" for item in status["org_title_registry"]["active_titles"])
    assert status["out_of_scope_departments"] == []
    assert "render_success_rate" in status["render_metrics"]
    cio_report = next(item for item in status["report_center"]["latest_reports"] if item["leader_name"] == "lead.cio")
    assert cio_report["report_payload"]["testing_and_stability"]["owner"] == "lead.cio"
    assert "render_success_rate" in cio_report["report_payload"]["testing_and_stability"]

    workflow_resp = await api_client.get("/api/cao/governance/workflow")
    assert workflow_resp.status_code == 200
    workflow = workflow_resp.json()
    assert workflow["workflow"]["dispatch_mode"] == "graph"
    assert workflow["scope"] == "company_system"
    assert workflow["workflow"]["main_route"][0] == "lead.cfo"
    assert "lead.qa" in workflow["workflow"]["main_route"]

    progress_resp = await api_client.get(f"/api/cao/governance/tasks/{workflow_run_id}/progress")
    assert progress_resp.status_code == 200
    progress = progress_resp.json()
    assert progress["task_id"] == workflow_run_id
    assert progress["progress_ratio"] >= 0
    assert "lead.cfo" in progress["stage_statuses"]
    assert "lead.qa" in progress["stage_statuses"]


@pytest.mark.asyncio
async def test_cao_governance_can_issue_optimize_command_and_manage_evolution(api_client):
    disable_resp = await api_client.post("/api/cao/governance/evolution/disable")
    assert disable_resp.status_code == 200
    assert disable_resp.json()["evolution_enabled"] is False

    optimize_resp = await api_client.post(
        "/api/cao/governance/leaders/lead.qa/optimize",
        json={"target_metric": "qa_pass_rate", "goal_value": 0.95},
    )
    assert optimize_resp.status_code == 200
    optimize_data = optimize_resp.json()
    assert optimize_data["command"]["leader_name"] == "lead.qa"
    assert optimize_data["command"]["target_metric"] == "qa_pass_rate"
    assert "leader_event" in optimize_data["command"]

    enable_resp = await api_client.post("/api/cao/governance/evolution/enable")
    assert enable_resp.status_code == 200
    assert enable_resp.json()["evolution_enabled"] is True

    cycle_resp = await api_client.post("/api/cao/governance/evolution/cycle")
    assert cycle_resp.status_code == 200
    cycle = cycle_resp.json()
    assert "company_status" in cycle
    assert "issued_commands" in cycle

    disable_resp = await api_client.post("/api/cao/governance/evolution/disable")
    assert disable_resp.status_code == 200
    assert disable_resp.json()["evolution_enabled"] is False


@pytest.mark.asyncio
async def test_cmo_chat_can_query_ceo_management_surface(api_client):
    response = await api_client.post(
        "/api/cmo/chat",
        json={"message": "查看公司状态"},
    )
    assert response.status_code == 200

    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    event_types = [event["type"] for event in events]
    assert "reply" in event_types
    assert "report" in event_types

    report_event = next(event for event in events if event["type"] == "report")
    assert report_event["source"] == "lead.promotion.report_ui"
    assert "Governance overview" in report_event["message"]


@pytest.mark.asyncio
async def test_cmo_chat_blocks_when_finance_gate_fails(api_client, monkeypatch):
    monkeypatch.setattr(settings.finance, "daily_budget", 0.0001)

    response = await api_client.post(
        "/api/cmo/chat",
        json={"message": "给龙虾门店运营做一条抖音视频，30秒"},
    )
    assert response.status_code == 200

    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    event_types = [event["type"] for event in events]
    assert "reply" in event_types
    assert "status" in event_types
    assert "error" in event_types
    assert "result" not in event_types

    failed_status = next(
        event
        for event in events
        if event["type"] == "status" and event["stage"] == "lead.cfo" and event["status"] == "failed"
    )
    error_event = next(event for event in events if event["type"] == "error")
    assert failed_status["source"] == "lead.promotion.progress_ui"
    assert "财务闸门" in error_event["message"] or "finance gate" in error_event["message"].lower()


@pytest.mark.asyncio
async def test_cao_governance_leader_status_exposes_department_report_template(api_client):
    response = await api_client.get("/api/cao/governance/leaders/lead.cio")
    assert response.status_code == 200
    leader = response.json()["leader"]
    assert leader["name"] == "lead.cio"
    assert leader["report_template"]["department_type"] == "information_hub"
    assert "knowledge_asset_count" in leader["report_template"]["focus_metrics"]
    assert leader["periodic_report_template"]["report_scope"] == "periodic"

    promotion_response = await api_client.get("/api/cao/governance/leaders/lead.promotion")
    assert promotion_response.status_code == 200
    promotion_leader = promotion_response.json()["leader"]
    assert promotion_leader["name"] == "lead.promotion"
    assert promotion_leader["report_template"]["department_type"] == "promotion_interface"
    assert promotion_leader["management_scope"]["direct_ceo_managed"] is True
    assert promotion_leader["management_scope"]["in_main_workflow_route"] is False
    assert promotion_leader["management_scope"]["user_facing"] is True
    assert promotion_leader["organization_profile"]["title_code"] == "CMO"

    cho_response = await api_client.get("/api/cao/governance/leaders/lead.cho")
    assert cho_response.status_code == 200
    cho_leader = cho_response.json()["leader"]
    assert cho_leader["name"] == "lead.cho"
    assert cho_leader["report_template"]["department_type"] == "public_agent_management"
    assert cho_leader["management_scope"]["public_agent_managed"] is True
    assert cho_leader["organization_profile"]["title_code"] == "CHO"

    cao_response = await api_client.get("/api/cao/governance/leaders/lead.publish")
    assert cao_response.status_code == 200
    cao_leader = cao_response.json()["leader"]
    assert cao_leader["report_template"]["department_type"] == "external_api_gateway"
    assert cao_leader["management_scope"]["external_api_managed"] is True
    assert cao_leader["organization_profile"]["title_code"] == "CAO"
    assert "CMO" in promotion_leader["organization_profile"]["executive_title"]


@pytest.mark.asyncio
async def test_cmo_chat_can_query_cto_status_by_title_alias(api_client):
    response = await api_client.post(
        "/api/cmo/chat",
        json={"message": "查看 CTO 状态"},
    )
    assert response.status_code == 200

    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    report_event = next(event for event in events if event["type"] == "report")
    assert "CTO" in report_event["message"]
    assert "lead.research_development" in report_event["leader"]["name"]


@pytest.mark.asyncio
async def test_cao_governance_can_collect_periodic_reports_and_query_latest(api_client):
    run_resp = await api_client.post(
        "/api/cao/workflows/runs",
        json={
            "domain": "report-cycle-check",
            "platform": "douyin",
            "hotspot_count": 6,
            "top_n": 2,
            "content_type": "knowledge",
            "style": "clean",
            "duration": 20,
            "auto_approve_script": False,
            "auto_generate_video": False,
        },
    )
    assert run_resp.status_code == 200

    collect_resp = await api_client.post("/api/cao/governance/reports/collect", json={"cadence": "daily"})
    assert collect_resp.status_code == 200
    collected = collect_resp.json()
    assert collected["count"] >= 10

    all_reports_resp = await api_client.get(
        "/api/cao/governance/reports",
        params={"leader_name": "lead.cio", "limit": 5},
    )
    assert all_reports_resp.status_code == 200
    all_reports = all_reports_resp.json()["reports"]
    assert len(all_reports) >= 1

    latest_resp = await api_client.get("/api/cao/governance/leaders/lead.cio/reports/latest")
    assert latest_resp.status_code == 200
    latest = latest_resp.json()["report"]
    assert latest["leader_name"] == "lead.cio"
    assert latest["report_payload"]["testing_and_stability"]["owner"] == "lead.cio"
    assert "workflow_success_rate" in latest["report_payload"]["testing_and_stability"]
    assert "render_success_rate" in latest["report_payload"]["testing_and_stability"]
    assert "render_success_rate" in latest["report_payload"]["testing_and_stability"]


@pytest.mark.asyncio
async def test_cao_governance_request_leader_report_creates_requested_report_record(api_client):
    response = await api_client.post("/api/cao/governance/leaders/lead.cfo/request-report")
    assert response.status_code == 200
    data = response.json()
    assert data["request"]["leader_name"] == "lead.cfo"
    assert data["report"]["leader_name"] == "lead.cfo"
    assert data["report"]["report_type"] == "requested"

