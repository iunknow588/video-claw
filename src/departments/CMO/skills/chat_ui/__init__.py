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

    LEADER_ALIASES = LEADER_QUERY_ALIASES

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        action = input_data.get("action")
        if action != "interpret_user_message":
            raise ValueError(f"Unsupported action for {self.skill_name}: {action}")

        message = str(input_data.get("message") or "").strip()
        if not message:
            return {
                "intent": "empty",
                "reply_message": (
                    "宣传部在岗。除了直接派视频任务，你也可以问我："
                    "查看生产状态、查看工作流，或者要求质检组优化合格率。"
                ),
            }

        lowered = message.lower()
        run_id = self._extract_run_id(lowered)
        leader_name = self._extract_leader_name(message)

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

        if leader_name and self._looks_like_optimize_command(message):
            target_metric = self._parse_target_metric(message)
            goal_value = self._parse_goal_value(message, target_metric)
            return {
                "intent": "optimize_request",
                "leader_name": leader_name,
                "target_metric": target_metric,
                "goal_value": goal_value,
                "reply_message": f"收到，我会把 {target_metric} 的优化目标发给 {self._leader_label(leader_name)}。",
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

        if self._looks_like_workflow_command(message):
            workflow_request = self._build_workflow_request(message)
            return {
                "intent": "workflow_request",
                "workflow_request": workflow_request,
                "reply_message": (
                    f"收到，我会先代表宣传部接单，再把“{workflow_request['domain']}”"
                    f"送入当前生产系统，按 {workflow_request['platform']} 平台推进。"
                ),
            }

        return {
            "intent": "help",
            "reply_message": (
                "我现在支持四类指令：\n"
                "1. 直接派活，例如“给龙虾运营做一条小红书视频”。\n"
                "2. 查记录，例如“查看最近任务”或“查看任务 <run_id> 进度”。\n"
                "3. 查管理面，例如“查看生产状态”“查看工作流”“列出一级 Leader”。\n"
                "4. 下优化命令，例如“让质检组把合格率提高到95%”。"
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

    def _build_workflow_request(self, message: str) -> dict[str, Any]:
        platform = self._parse_platform(message)
        duration = self._parse_duration(message)
        style = self._parse_style(message)
        domain = self._parse_domain(message, platform)
        auto_generate_video = "脚本" not in message or "视频" in message or "发布" in message
        auto_approve_script = auto_generate_video or "自动审核" in message or "直接过审" in message

        return {
            "domain": domain,
            "platform": platform,
            "hotspot_count": 12,
            "top_n": 3,
            "content_type": "knowledge",
            "style": style,
            "video_style": "realistic" if auto_generate_video else style,
            "duration": duration,
            "audience": None,
            "publish_goal": message[:100],
            "auto_approve_script": auto_approve_script,
            "auto_generate_video": auto_generate_video,
        }

    def _parse_platform(self, message: str) -> str:
        mapping = {
            "抖音": "douyin",
            "douyin": "douyin",
            "小红书": "xiaohongshu",
            "xiaohongshu": "xiaohongshu",
            "b站": "bilibili",
            "bilibili": "bilibili",
        }
        lowered = message.lower()
        for keyword, platform in mapping.items():
            if keyword in lowered or keyword in message:
                return platform
        return "douyin"

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
        return "clean"

    def _parse_domain(self, message: str, platform: str) -> str:
        patterns = [
            r"(?:给|做|围绕|关于)(.+?)(?:做一条|生成|发布|视频|脚本)",
            r"在(.+?)领域",
            r"(.+?)(?:抖音|小红书|b站|bilibili|douyin|xiaohongshu)",
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
            .replace(platform, " ")
        )
        return fallback or "通用内容运营"

    def _clean_domain(self, domain: str) -> str:
        cleaned = re.sub(r"[，。,.!！？;；]", " ", domain)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" 的关于让帮我做个一条")
        return cleaned.strip()[:100]
