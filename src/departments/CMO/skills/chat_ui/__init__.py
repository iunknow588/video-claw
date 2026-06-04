from __future__ import annotations

import re
from typing import Any

from departments.CEO.leaders.organization import LEADER_QUERY_ALIASES, LEADER_STAGE_LABELS_CN
from departments.CEO.skills.base import BaseSkill


class ChatUISkill(BaseSkill):
    skill_name = "lead.promotion.chat_ui"
    description = "Interprets incoming user chat into promotion-side task directives and production-governance queries."
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["interpret_user_message"],
            },
            "message": {"type": "string"},
            "workflow_params": {"type": "object"},
        },
        "required": ["action"],
    }
    tags = ["lead", "promotion", "ui", "chat"]
    dependencies = []
    required_tokens = ["message"]

    WORKFLOW_KEYWORDS = (
        "视频",
        "发布",
        "做一条",
        "生成",
        "脚本",
        "选题",
        "内容",
    )
    RECENT_RUNS_KEYWORDS = (
        "最近任务",
        "历史任务",
        "查看任务",
        "任务列表",
        "最近运行",
        "run list",
    )
    TRACE_KEYWORDS = ("进度", "状态", "报告", "trace", "详情")
    COMPANY_STATUS_KEYWORDS = (
        "公司状态",
        "公司总览",
        "运营总览",
        "整体情况",
        "生产状态",
        "生产总览",
        "kpi",
        "成功率",
        "合格率",
        "通过率",
    )
    WORKFLOW_STATUS_KEYWORDS = ("工作流", "流程结构", "workflow", "主链路", "执行图")
    LEADER_LIST_KEYWORDS = ("leader列表", "部门列表", "组织架构", "有哪些leader", "有哪些部门", "列出leader")
    LEADER_STATUS_KEYWORDS = ("状态", "绩效", "预算", "指标", "配额")
    LEADER_REPORT_KEYWORDS = ("报告", "汇报", "分析报告")
    OPTIMIZE_KEYWORDS = ("优化", "提升", "提高", "增强", "改进")
    ENABLE_EVOLUTION_KEYWORDS = ("开启进化", "打开进化", "启用进化")
    DISABLE_EVOLUTION_KEYWORDS = ("关闭进化", "停用进化", "禁用进化", "停止进化")
    EVOLUTION_CYCLE_KEYWORDS = ("进化循环", "进化闭环", "触发进化", "手动进化")
    DEFAULT_WORKFLOW_PROMPT_GUIDE = "请直接说明要创作的视频类型、主题、目标平台、风格和时长。"
    DEFAULT_WORKFLOW_PROMPT_EXAMPLE = (
        "例如：做一条知识讲解视频，类型偏知识讲解类，主题是龙虾门店运营，目标平台是小红书，"
        "面向餐饮老板和门店店长，目标是提升专业感知与咨询转化，风格专业干净，时长60秒。"
    )
    CONTENT_TYPE_MAPPING = {
        "knowledge": ("知识讲解类", ("知识讲解", "科普", "教程", "教学", "拆解", "干货")),
        "news": ("热点口播类", ("热点口播", "热点解读", "资讯快讯", "新闻快讯", "快讯", "口播")),
        "review": ("测评对比类", ("测评对比", "评测", "测评", "对比", "横评")),
        "story": ("剧情演绎类", ("剧情演绎", "剧情", "故事", "情景短剧", "短剧", "演绎")),
        "product": ("种草推荐类", ("种草推荐", "种草", "推荐", "带货", "开箱")),
    }
    PLATFORM_LABELS = {
        "douyin": "抖音",
        "xiaohongshu": "小红书",
        "xigua": "西瓜视频",
        "bilibili": "B站",
    }

    LEADER_ALIASES = LEADER_QUERY_ALIASES

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        action = input_data.get("action")
        if action != "interpret_user_message":
            raise ValueError(f"Unsupported action for {self.skill_name}: {action}")

        message = str(input_data.get("message") or "").strip()
        workflow_params = self._normalize_workflow_params(input_data.get("workflow_params"))
        if not message and not workflow_params:
            return {
                "intent": "empty",
                "reply_message": (
                    "宣传部在岗。除了直接派视频任务，你也可以问我："
                    "查看生产状态、查看工作流。节点优化由 CEO 配置通道统一管理，聊天窗口不接收优化指令。"
                    f"{self.DEFAULT_WORKFLOW_PROMPT_GUIDE}{self.DEFAULT_WORKFLOW_PROMPT_EXAMPLE}"
                ),
            }

        lowered = message.lower()
        run_id = self._extract_run_id(lowered)
        leader_name = self._extract_leader_name(message)
        workflow_like = self._looks_like_workflow_command(message) or self._has_structured_workflow_intent(workflow_params)

        if self._is_recent_runs_query(lowered):
            return {
                "intent": "recent_runs",
                "reply_message": "收到，我来调取最近任务给你看。",
            }

        if run_id and self._is_trace_query(lowered):
            return {
                "intent": "trace_request",
                "run_id": run_id,
                "reply_message": f"收到，我来整理任务 {run_id} 的执行链路。",
            }

        if workflow_like:
            workflow_request = self._build_workflow_request(message, workflow_params=workflow_params)
            return {
                "intent": "workflow_request",
                "workflow_request": workflow_request,
                "reply_message": (
                    f"收到，我会先代表宣传部接单，再把“{workflow_request['domain']}”"
                    f"送入当前生产系统，按 {self._platform_label(workflow_request['platform'])} 平台推进，"
                    f"视频类型按 {self._content_type_label(workflow_request['content_type'])} 处理。"
                ),
            }

        if leader_name and self._looks_like_optimize_command(message):
            return {
                "intent": "ceo_config_only",
                "reply_message": (
                    f"收到，但 {self._leader_label(leader_name)} 的优化不再通过聊天命令下发。"
                    "请改为由 CEO 在配置通道中统一调整节点配置、预算或资源。"
                ),
            }

        if leader_name and self._looks_like_leader_report_request(lowered):
            return {
                "intent": "leader_report_request",
                "leader_name": leader_name,
                "reply_message": f"收到，我来要求 {self._leader_label(leader_name)} 提交一份详细报告。",
            }

        if leader_name and self._looks_like_leader_status_query(lowered):
            return {
                "intent": "leader_status",
                "leader_name": leader_name,
                "reply_message": f"收到，我来查看 {self._leader_label(leader_name)} 的当前状态。",
            }

        if self._is_company_status_query(message):
            return {
                "intent": "company_status",
                "reply_message": "收到，我来汇总当前生产治理总览。",
            }

        if self._is_workflow_snapshot_query(message):
            return {
                "intent": "workflow_snapshot",
                "reply_message": "收到，我来展示当前工作流骨架和排序关系。",
            }

        if self._is_leader_list_query(message):
            return {
                "intent": "leader_list",
                "reply_message": "收到，我来列出当前一级 Leader 与归属部门。",
            }

        if self._is_enable_evolution_query(message):
            return {
                "intent": "enable_evolution",
                "reply_message": "收到，我来打开治理演进开关。",
            }

        if self._is_disable_evolution_query(message):
            return {
                "intent": "disable_evolution",
                "reply_message": "收到，我来关闭治理演进开关。",
            }

        if self._is_evolution_cycle_query(message):
            return {
                "intent": "evolution_cycle",
                "reply_message": "收到，我来手动触发一轮治理演进闭环。",
            }

        return {
            "intent": "help",
            "reply_message": (
                "我现在支持四类指令：\n"
                f"1. 直接派活。{self.DEFAULT_WORKFLOW_PROMPT_GUIDE}"
                f"例如“{self.DEFAULT_WORKFLOW_PROMPT_EXAMPLE[:-1]}”。\n"
                "2. 查记录，例如“查看最近任务”或“查看任务 <run_id> 进度”。\n"
                "3. 查管理面，例如“查看生产状态”“查看工作流”“列出一级 Leader”。\n"
                "4. 节点优化由 CEO 配置通道统一管理，聊天窗口不接收优化指令。"
            ),
        }

    def _looks_like_workflow_command(self, message: str) -> bool:
        return any(keyword in message for keyword in self.WORKFLOW_KEYWORDS)

    def _is_recent_runs_query(self, lowered: str) -> bool:
        return any(keyword in lowered for keyword in self.RECENT_RUNS_KEYWORDS) and not self._extract_run_id(lowered)

    def _is_trace_query(self, lowered: str) -> bool:
        return any(keyword in lowered for keyword in self.TRACE_KEYWORDS)

    def _is_company_status_query(self, message: str) -> bool:
        lowered = message.lower()
        return any(keyword in lowered or keyword in message for keyword in self.COMPANY_STATUS_KEYWORDS)

    def _is_workflow_snapshot_query(self, message: str) -> bool:
        lowered = message.lower()
        return any(keyword in lowered or keyword in message for keyword in self.WORKFLOW_STATUS_KEYWORDS)

    def _is_leader_list_query(self, message: str) -> bool:
        lowered = message.lower()
        return any(keyword in lowered or keyword in message for keyword in self.LEADER_LIST_KEYWORDS)

    def _looks_like_leader_status_query(self, lowered: str) -> bool:
        return any(keyword in lowered for keyword in self.LEADER_STATUS_KEYWORDS)

    def _looks_like_leader_report_request(self, lowered: str) -> bool:
        return any(keyword in lowered for keyword in self.LEADER_REPORT_KEYWORDS)

    def _looks_like_optimize_command(self, message: str) -> bool:
        lowered = message.lower()
        return any(keyword in lowered or keyword in message for keyword in self.OPTIMIZE_KEYWORDS)

    def _is_enable_evolution_query(self, message: str) -> bool:
        lowered = message.lower()
        return any(keyword in lowered or keyword in message for keyword in self.ENABLE_EVOLUTION_KEYWORDS)

    def _is_disable_evolution_query(self, message: str) -> bool:
        lowered = message.lower()
        return any(keyword in lowered or keyword in message for keyword in self.DISABLE_EVOLUTION_KEYWORDS)

    def _is_evolution_cycle_query(self, message: str) -> bool:
        lowered = message.lower()
        return any(keyword in lowered or keyword in message for keyword in self.EVOLUTION_CYCLE_KEYWORDS)

    def _extract_run_id(self, lowered: str) -> str | None:
        pattern = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
        match = pattern.search(lowered)
        return match.group(0) if match else None

    def _extract_leader_name(self, message: str) -> str | None:
        lowered = message.lower()
        for leader_name, aliases in self.LEADER_ALIASES.items():
            for alias in aliases:
                if alias in lowered or alias in message:
                    return leader_name
        return None

    def _parse_target_metric(self, message: str) -> str:
        lowered = message.lower()
        if "合格率" in message or "通过率" in message:
            return "qa_pass_rate"
        if "成功率" in message:
            return "workflow_success_rate"
        if "耗时" in message or "时延" in message:
            return "average_duration_ms"
        if "token" in lowered or "预算" in message or "配额" in message:
            return "token_efficiency"
        return "quality_score"

    def _parse_goal_value(self, message: str, target_metric: str) -> float | str:
        percent_match = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%", message)
        if percent_match:
            return round(float(percent_match.group(1)) / 100, 4)

        value_match = re.search(r"(?:到|至|为|达到)\s*(\d+(?:\.\d+)?)", message)
        if value_match:
            value = float(value_match.group(1))
            if target_metric.endswith("_rate") or "rate" in target_metric:
                return round(value / 100, 4) if value > 1 else round(value, 4)
            return round(value, 4)

        if target_metric in {"qa_pass_rate", "workflow_success_rate", "quality_score"}:
            return 0.95
        if target_metric == "token_efficiency":
            return 0.85
        return "improve"

    def _leader_label(self, leader_name: str) -> str:
        return LEADER_STAGE_LABELS_CN.get(leader_name, leader_name)

    def _build_workflow_request(
        self,
        message: str,
        *,
        workflow_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workflow_params = workflow_params or {}
        platform = str(workflow_params.get("platform") or self._parse_platform(message))
        content_type = str(workflow_params.get("content_type") or self._parse_content_type(message))
        duration = int(workflow_params.get("duration") or self._parse_duration(message))
        style = str(workflow_params.get("style") or self._parse_style(message))
        domain = self._clean_domain(str(workflow_params.get("domain") or "")) or self._parse_domain(message, platform)
        audience = self._clean_optional_text(workflow_params.get("audience")) or self._parse_audience(message)
        publish_goal = self._clean_optional_text(workflow_params.get("publish_goal")) or self._parse_publish_goal(message)
        auto_generate_video = self._resolve_auto_generate_video(message, workflow_params)
        auto_approve_script = self._resolve_auto_approve_script(message, workflow_params, auto_generate_video)
        video_style = self._clean_optional_text(workflow_params.get("video_style")) or self._resolve_video_style(
            content_type=content_type,
            style=style,
        )

        return {
            "domain": domain,
            "platform": platform,
            "hotspot_count": 12,
            "top_n": 3,
            "content_type": content_type,
            "style": style,
            "video_style": video_style if auto_generate_video else style,
            "duration": duration,
            "audience": audience,
            "publish_goal": publish_goal or self._default_publish_goal(domain, message, content_type=content_type),
            "auto_approve_script": auto_approve_script,
            "auto_generate_video": auto_generate_video,
        }

    def _normalize_workflow_params(self, workflow_params: Any) -> dict[str, Any]:
        if not isinstance(workflow_params, dict):
            return {}
        normalized: dict[str, Any] = {}
        for key, value in workflow_params.items():
            if value is None:
                continue
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    normalized[key] = cleaned
                continue
            normalized[key] = value
        return normalized

    def _has_structured_workflow_intent(self, workflow_params: dict[str, Any]) -> bool:
        if not workflow_params:
            return False
        return any(
            workflow_params.get(field)
            for field in ("domain", "content_type", "platform", "publish_goal", "audience")
        )

    def _clean_optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    def _resolve_auto_generate_video(self, message: str, workflow_params: dict[str, Any]) -> bool:
        if "auto_generate_video" in workflow_params:
            return bool(workflow_params["auto_generate_video"])
        return "脚本" not in message or "视频" in message or "发布" in message or not message

    def _resolve_auto_approve_script(
        self,
        message: str,
        workflow_params: dict[str, Any],
        auto_generate_video: bool,
    ) -> bool:
        if "auto_approve_script" in workflow_params:
            return bool(workflow_params["auto_approve_script"])
        lowered = message.lower()
        if any(keyword in message or keyword in lowered for keyword in ("自动审核", "直接过审", "自动过审", "无需审核")):
            return True
        # 简单派活默认直接推进到成片，详细创作简报则默认保留人工脚本审核。
        detailed_brief_markers = (
            "类型",
            "目标平台",
            "风格",
            "面向",
            "目标是",
            "目标为",
            "知识讲解类",
            "热点口播类",
            "测评对比类",
            "剧情演绎类",
            "种草推荐类",
        )
        if any(marker in message for marker in detailed_brief_markers):
            return False
        return auto_generate_video

    def _default_publish_goal(self, domain: str, message: str, *, content_type: str) -> str:
        goal_map = {
            "knowledge": "提升专业感知与咨询转化",
            "news": "提升互动率与热点跟进效率",
            "review": "提升对比转化与咨询意向",
            "story": "提升完播率与账号记忆点",
            "product": "提升种草转化与私信咨询",
        }
        if domain and "门店" in domain and content_type == "knowledge":
            return "提升专业感知与咨询转化"
        return goal_map.get(content_type, f"{domain}内容生产" if domain else "提升内容转化")

    def _parse_platform(self, message: str) -> str:
        mapping = {
            "抖音": "douyin",
            "douyin": "douyin",
            "小红书": "xiaohongshu",
            "xiaohongshu": "xiaohongshu",
            "西瓜": "xigua",
            "西瓜视频": "xigua",
            "xigua": "xigua",
            "b站": "bilibili",
            "bilibili": "bilibili",
        }
        lowered = message.lower()
        for keyword, platform in mapping.items():
            if keyword in lowered or keyword in message:
                return platform
        return "douyin"

    def _parse_content_type(self, message: str) -> str:
        lowered = message.lower()
        for content_type, (_label, keywords) in self.CONTENT_TYPE_MAPPING.items():
            for keyword in keywords:
                if keyword in message or keyword in lowered:
                    return content_type
        return "knowledge"

    def _parse_duration(self, message: str) -> int:
        match = re.search(r"(\d{1,3})\s*(秒|s|sec)", message, flags=re.IGNORECASE)
        if not match:
            return 30
        return max(5, min(180, int(match.group(1))))

    def _parse_style(self, message: str) -> str:
        if "快节奏" in message or "迅速" in message:
            return "fast"
        if "专业" in message or "干净" in message:
            return "clean"
        if "剧情" in message or "故事感" in message:
            return "story"
        return "clean"

    def _parse_audience(self, message: str) -> str | None:
        patterns = [
            r"(?:面向)(.+?)(?:，|,|。|$)",
            r"(?:面向|给)(.+?)(?:看|用户|人群|观众|，|,|。|$)",
            r"(?:受众|人群)(?:是|为)?(.+?)(?:，|,|。|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, flags=re.IGNORECASE)
            if match:
                audience = self._clean_domain(match.group(1))
                if audience:
                    return audience
        return None

    def _parse_publish_goal(self, message: str) -> str | None:
        patterns = [
            r"(?:目标是|目标为|用于|希望|想要)(.+?)(?:，|,|。|$)",
            r"(?:提升|提高)(.+?)(?:，|,|。|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, flags=re.IGNORECASE)
            if match:
                goal = self._clean_domain(match.group(1))
                if goal:
                    if pattern.startswith("(?:提升|提高)"):
                        return f"提升{goal}"
                    return goal
        return None

    def _resolve_video_style(self, *, content_type: str, style: str) -> str:
        if content_type == "story":
            return "cinematic"
        if content_type in {"news", "review"} or style == "fast":
            return "dynamic"
        return "realistic"

    def _content_type_label(self, content_type: str) -> str:
        item = self.CONTENT_TYPE_MAPPING.get(content_type)
        return item[0] if item else content_type

    def _platform_label(self, platform: str) -> str:
        return self.PLATFORM_LABELS.get(platform, platform)

    def _parse_domain(self, message: str, platform: str) -> str:
        patterns = [
            r"(?:主题|方向|选题)(?:是|为)?(.+?)(?:，|,|。|$)",
            r"(?:关于|围绕)(.+?)(?:创作|制作|做一条|生成|发布|视频|脚本|，|,|。|$)",
            r"(?:给|做|围绕|关于)(.+?)(?:做一条|生成|发布|视频|脚本)",
            r"在(.+?)领域",
            r"(.+?)(?:抖音|小红书|西瓜视频|西瓜|b站|bilibili|douyin|xiaohongshu|xigua)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, flags=re.IGNORECASE)
            if match:
                domain = self._clean_domain(match.group(1))
                if domain:
                    return domain

        fallback = self._clean_domain(
            message.replace("做一条", " ")
            .replace("生成", " ")
            .replace("发布", " ")
            .replace("视频", " ")
            .replace("脚本", " ")
            .replace("知识讲解类", " ")
            .replace("热点口播类", " ")
            .replace("测评对比类", " ")
            .replace("剧情演绎类", " ")
            .replace("种草推荐类", " ")
            .replace(platform, " ")
        )
        return fallback or "通用内容运营"

    def _clean_domain(self, domain: str) -> str:
        cleaned = re.sub(r"[，。,.!！？;；]", " ", domain)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" 的关于让帮我做个一条")
        return cleaned.strip()[:100]
