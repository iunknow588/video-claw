import json

import pytest

from departments.CMO.skills.chat_ui import ChatUISkill


def test_chat_ui_prefers_structured_workflow_params_over_message_guess():
    result = ChatUISkill().execute(
        {
            "action": "interpret_user_message",
            "message": "make a short video",
            "workflow_params": {
                "domain": "龙虾门店运营",
                "platform": "xiaohongshu",
                "content_type": "review",
                "style": "fast",
                "video_style": "dynamic",
                "duration": 45,
                "audience": "餐饮老板",
                "publish_goal": "提升到店转化",
                "auto_approve_script": False,
                "auto_generate_video": False,
            },
        }
    )

    assert result["intent"] == "workflow_request"
    request = result["workflow_request"]
    assert request["domain"] == "龙虾门店运营"
    assert request["platform"] == "xiaohongshu"
    assert request["content_type"] == "review"
    assert request["style"] == "fast"
    assert request["video_style"] == "fast"
    assert request["duration"] == 45
    assert request["audience"] == "餐饮老板"
    assert request["publish_goal"] == "提升到店转化"
    assert request["auto_approve_script"] is False
    assert request["auto_generate_video"] is False


def test_chat_ui_can_launch_workflow_from_structured_params_without_workflow_keywords():
    result = ChatUISkill().execute(
        {
            "action": "interpret_user_message",
            "message": "start this",
            "workflow_params": {
                "domain": "龙虾新品推广",
                "platform": "douyin",
                "content_type": "knowledge",
            },
        }
    )

    assert result["intent"] == "workflow_request"
    assert result["workflow_request"]["domain"] == "龙虾新品推广"
    assert result["workflow_request"]["platform"] == "douyin"
    assert result["workflow_request"]["content_type"] == "knowledge"


@pytest.mark.asyncio
async def test_cmo_chat_accepts_structured_workflow_params(api_client):
    response = await api_client.post(
        "/api/cmo/chat",
        json={
            "message": "start this",
            "workflow_params": {
                "domain": "龙虾门店运营",
                "platform": "xiaohongshu",
                "content_type": "review",
                "style": "fast",
                "video_style": "dynamic",
                "duration": 45,
                "audience": "餐饮老板",
                "publish_goal": "提升到店转化",
                "auto_approve_script": False,
                "auto_generate_video": False,
            },
        },
    )
    assert response.status_code == 200

    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    result_event = next(event for event in events if event["type"] == "result")
    result = result_event["result"]

    assert result["domain"] == "龙虾门店运营"
    assert result["platform"] == "xiaohongshu"
    assert result["script_status"] == "pending_review"
    assert result["video_task_id"] is None
    assert result["qa_status"] == "passed"
