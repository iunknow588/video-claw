from departments.CMO.skills.chat_ui import ChatUISkill


def test_workflow_prompt_with_improve_goal_is_not_misclassified_as_optimize_request():
    skill = ChatUISkill()

    result = skill.execute(
        {
            "action": "interpret_user_message",
            "message": (
                "做一条知识讲解视频，类型偏知识讲解类，主题是面包制作，目标平台是小红书，"
                "面向宝爸宝妈，目标是提高生活质量，风格专业干净，时长60秒。"
            ),
        }
    )

    assert result["intent"] == "workflow_request"
    assert result["workflow_request"]["domain"] == "面包制作"
    assert result["workflow_request"]["platform"] == "xiaohongshu"
    assert result["workflow_request"]["content_type"] == "knowledge"
    assert result["workflow_request"]["publish_goal"] == "提高生活质量"


def test_optimize_request_is_redirected_to_ceo_config_channel():
    skill = ChatUISkill()

    result = skill.execute(
        {
            "action": "interpret_user_message",
            "message": "请让制作负责人把 quality_score 提高到0.95。",
        }
    )

    assert result["intent"] == "ceo_config_only"
    assert "CEO" in result["reply_message"]
    assert "配置通道" in result["reply_message"]
