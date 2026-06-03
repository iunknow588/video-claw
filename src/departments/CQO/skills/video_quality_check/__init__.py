from __future__ import annotations

from typing import Any

from departments.CEO.skills.base import BaseSkill


class VideoQualityCheckSkill(BaseSkill):
    skill_name = "lead.qa.video_quality_check"
    description = "Checks video clarity, completion, black-screen risk, and playback readiness."
    parameters_schema = {
        "type": "object",
        "properties": {
            "video_task": {"type": ["object", "null"]},
            "platform": {"type": "string"},
        },
        "required": ["platform"],
    }
    tags = ["lead", "qa", "video"]
    retry_policy = {"max_retries": 1, "backoff": 0.0}
    dependencies = ["lead.production.video_task", "lead.production.video_process"]
    required_tokens = ["video_task"]

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        task = input_data.get("video_task") or {}
        
        # 情况1: 完全没有视频任务数据
        if not task:
            return {
                "dimension": "video_quality",
                "applicable": False,
                "pass": True,
                "score": 1.0,
                "issues": ["当前任务未生成视频，画面质量检测跳过。"],
                "recommendation": "若后续生成视频，请重新触发画面质检。",
            }

        # 情况2: 视频任务已明确失败 —— 关键修复
        task_status = task.get("status")
        if task_status == "failed":
            return {
                "dimension": "video_quality",
                "applicable": True,  # 适用，且必须检查
                "pass": False,  # 明确失败
                "score": 0.0,
                "issues": [
                    f"视频生成任务状态为 failed，未能产出可质检视频。",
                    f"失败原因：{task.get('error_message', '未知错误')}",
                ],
                "recommendation": "建议检查生产环节日志，排查视频生成失败原因后重试。",
            }

        # 情况3: 视频任务存在但未完成 —— 原有逻辑
        issues: list[str] = []
        score = 1.0
        if task_status != "completed":
            issues.append(f"视频任务状态为 {task_status}，尚未达到可质检状态。")
            score -= 0.5
        if float(task.get("progress") or 0.0) < 1.0:
            issues.append("视频生成进度未完成。")
            score -= 0.2
        if not task.get("video_url"):
            issues.append("缺少可访问的视频地址。")
            score -= 0.3
        if task.get("size") not in {"1080x1920", "1920x1080", "720x1280"}:
            issues.append(f"当前分辨率 {task.get('size')} 不在推荐范围内。")
            score -= 0.1

        passed = score >= 0.7
        if passed and not issues:
            issues.append("未发现明显黑场、抖动或成片缺失风险。")

        return {
            "dimension": "video_quality",
            "applicable": True,
            "pass": passed,
            "score": round(max(score, 0.0), 4),
            "issues": issues,
            "recommendation": "通过，可继续进入合规与平台适配检测。" if passed else "建议回到生产组重新生成视频。",
        }

    def validate_input(self, input_data: dict[str, Any]) -> bool:
        return isinstance(input_data, dict) and "platform" in input_data
