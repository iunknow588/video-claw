from departments.CMO.skills.chat_ui import ChatUISkill
from departments.CSO.skills.domain_query_expansion import DomainQueryExpansionSkill


def test_chat_ui_prompt_guide_mentions_video_type_and_platform():
    skill = ChatUISkill()

    empty_result = skill.execute({"action": "interpret_user_message", "message": ""})
    help_result = skill.execute({"action": "interpret_user_message", "message": "hello"})

    assert "视频类型" in empty_result["reply_message"]
    assert "知识讲解视频" in empty_result["reply_message"]
    assert "小红书" in empty_result["reply_message"]
    assert "视频类型" in help_result["reply_message"]
    assert "知识讲解视频" in help_result["reply_message"]


def test_chat_ui_builds_workflow_request_from_video_type_prompt():
    skill = ChatUISkill()

    result = skill.execute(
        {
            "action": "interpret_user_message",
            "message": "做一条测评对比类视频，主题是龙虾半成品，目标平台是抖音，风格快节奏，时长30秒，面向餐饮老板，目标是提升到店转化。",
        }
    )

    request = result["workflow_request"]
    assert request["content_type"] == "review"
    assert request["platform"] == "douyin"
    assert request["style"] == "fast"
    assert request["video_style"] == "dynamic"
    assert request["duration"] == 30
    assert request["domain"] == "龙虾半成品"
    assert request["audience"] == "餐饮老板"
    assert request["publish_goal"] == "提升到店转化"


def test_chat_ui_reply_mentions_content_type_label():
    skill = ChatUISkill()

    result = skill.execute(
        {
            "action": "interpret_user_message",
            "message": "做一条剧情演绎类视频，主题是夜宵门店冲突，目标平台是B站。",
        }
    )

    assert "剧情演绎类" in result["reply_message"]
    assert "B站" in result["reply_message"]


def test_domain_query_expansion_uses_business_labels():
    result = DomainQueryExpansionSkill().run(
        {
            "domain": "龙虾门店运营",
            "platform": "xiaohongshu",
            "content_type": "knowledge",
            "audience": "餐饮创业者",
            "publish_goal": "提升完播率",
        }
    )

    assert "龙虾门店运营 知识讲解类" in result["expanded_queries"]
    assert "小红书 龙虾门店运营" in result["expanded_queries"]
