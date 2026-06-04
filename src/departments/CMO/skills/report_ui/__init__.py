from __future__ import annotations

from typing import Any

from departments.CEO.leaders.organization import LEADER_STAGE_LABELS_EN
from departments.CEO.skills.base import BaseSkill


class ReportUISkill(BaseSkill):
    skill_name = "lead.promotion.report_ui"
    description = "Formats production reports, trace summaries, governance snapshots, and errors for the external UI."
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "format_recent_runs",
                    "format_trace_report",
                    "format_workflow_result",
                    "format_company_status",
                    "format_workflow_snapshot",
                    "format_leader_status",
                    "format_evolution_report",
                    "format_error",
                    "format_reply",
                ],
            },
            "runs": {"type": "array"},
            "run": {"type": "object"},
            "summary": {"type": "object"},
            "result": {"type": "object"},
            "status": {"type": "object"},
            "workflow": {"type": "object"},
            "leader": {"type": "object"},
            "evolution": {"type": "object"},
            "message": {"type": "string"},
        },
        "required": ["action"],
    }
    tags = ["lead", "promotion", "ui", "report"]
    dependencies = ["lead.cfo.charge", "lead.cio.query_log", "lead.qa", "lead.publish"]
    required_tokens = ["summary", "result", "runs", "status", "workflow", "leader", "evolution"]

    STAGE_LABELS = LEADER_STAGE_LABELS_EN

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        action = input_data.get("action")
        if action == "format_recent_runs":
            return {"event": self._format_recent_runs(input_data.get("runs") or [])}
        if action == "format_trace_report":
            return {
                "event": self._format_trace_report(
                    run=input_data.get("run") or {},
                    summary=input_data.get("summary") or {},
                )
            }
        if action == "format_workflow_result":
            return {
                "event": self._format_workflow_result(
                    result=input_data.get("result") or {},
                    summary=input_data.get("summary") or {},
                )
            }
        if action == "format_company_status":
            return {"event": self._format_company_status(input_data.get("status") or {})}
        if action == "format_workflow_snapshot":
            return {"event": self._format_workflow_snapshot(input_data.get("workflow") or {})}
        if action == "format_leader_status":
            return {"event": self._format_leader_status(input_data.get("leader") or {})}
        if action == "format_evolution_report":
            return {"event": self._format_evolution_report(input_data.get("evolution") or {})}
        if action == "format_error":
            return {"event": self._format_error(str(input_data.get("message") or "Promotion channel error."))}
        if action == "format_reply":
            return {"event": self._format_reply(str(input_data.get("message") or ""))}
        raise ValueError(f"Unsupported action for {self.skill_name}: {action}")

    def _format_recent_runs(self, runs: list[dict[str, Any]]) -> dict[str, Any]:
        if not runs:
            return self._format_reply("No recent runs yet. Send a new task through Promotion to start the pipeline.")

        summary_lines = [
            f"{item['uuid']} | {item['domain']} | {item['platform']} | {item['status']}"
            for item in runs
        ]
        return {
            "type": "report",
            "message": "Promotion has organized the latest runs:\n" + "\n".join(summary_lines),
            "runs": runs,
            "source": self.skill_name,
            "channel": "promotion_ui",
        }

    def _format_trace_report(self, *, run: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
        trace_id = summary.get("trace_id") or run.get("trace_id") or "n/a"
        total_tokens = summary.get("total_tokens", 0)
        failed_steps = len(summary.get("failed_steps") or [])
        message = (
            f"Task {run.get('uuid')} status: {run.get('status')}\n"
            f"Domain: {run.get('domain')}\n"
            f"Platform: {run.get('platform')}\n"
            f"Trace ID: {trace_id}\n"
            f"Total tokens: {total_tokens}\n"
            f"Failed steps: {failed_steps}"
        )
        return {
            "type": "report",
            "message": message,
            "run": run,
            "summary": summary,
            "source": self.skill_name,
            "channel": "promotion_ui",
        }

    def _format_workflow_result(self, *, result: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
        parts = [
            f"Task completed: {result.get('domain')} / {result.get('platform')}",
            f"Script status: {result.get('script_status')}",
        ]
        if result.get("qa_status"):
            parts.append(f"QA status: {result.get('qa_status')}")
        if result.get("video_task_id"):
            parts.append(f"Video status: {result.get('video_status')}")
        if result.get("video_url"):
            parts.append(f"Video URL: {result.get('video_url')}")
        parts.append(f"Workflow run ID: {result.get('workflow_run_id')}")
        parts.append(f"Total tokens: {summary.get('total_tokens', 0)}")
        return {
            "type": "result",
            "message": "\n".join(parts),
            "result": result,
            "summary": summary,
            "source": self.skill_name,
            "channel": "promotion_ui",
        }

    def _format_company_status(self, status: dict[str, Any]) -> dict[str, Any]:
        run_metrics = status.get("run_metrics") or {}
        quality_metrics = status.get("quality_metrics") or {}
        finance_metrics = status.get("finance_metrics") or {}
        information_metrics = status.get("information_metrics") or {}
        weakest = status.get("weakest_leader")
        message = (
            "生产治理总览 / Governance overview:\n"
            f"Total runs: {run_metrics.get('total_runs', 0)}\n"
            f"Overall success rate: {self._percent(run_metrics.get('success_rate', 0.0))}\n"
            f"Average duration: {round(float(run_metrics.get('avg_duration_ms', 0.0) or 0.0), 2)} ms\n"
            f"QA pass rate: {self._percent(quality_metrics.get('qa_pass_rate', 0.0))}\n"
            f"Active leaders: {status.get('active_leader_count', 0)}\n"
            f"Pending config actions: {status.get('pending_config_actions', 0)}\n"
            f"Evolution: {'enabled' if status.get('evolution_enabled') else 'disabled'}"
        )
        if weakest:
            message += f"\nCurrent weakest leader: {self._stage_label(weakest)}"
        if finance_metrics:
            message += (
                "\nFinance remaining budget: "
                f"{finance_metrics.get('remaining_budget', 0.0)} {finance_metrics.get('currency', 'USD')}"
            )
        if information_metrics:
            message += (
                "\nCIO assets / logs: "
                f"{information_metrics.get('artifact_count', 0)} / {information_metrics.get('log_record_count', 0)}"
            )
        if status.get("non_workflow_leaders"):
            message += "\nManaged support departments: " + ", ".join(
                self._stage_label(str(item)) for item in status.get("non_workflow_leaders") or []
            )
        title_registry = status.get("org_title_registry") or {}
        active_titles = title_registry.get("active_titles") or []
        if active_titles:
            message += "\nActive executive titles: " + ", ".join(
                str(item.get("title_code")) for item in active_titles if item.get("title_code")
            )
        if status.get("governance_note"):
            message += "\nGovernance note: " + str(status.get("governance_note"))
        if status.get("out_of_scope_departments"):
            message += "\nOut of scope: " + ", ".join(str(item) for item in status.get("out_of_scope_departments") or [])
        return {
            "type": "report",
            "message": message,
            "status": status,
            "source": self.skill_name,
            "channel": "promotion_ui",
        }

    def _format_workflow_snapshot(self, workflow: dict[str, Any]) -> dict[str, Any]:
        route = workflow.get("main_route") or []
        message = (
            "Current workflow graph:\n"
            f"Version: {workflow.get('version', 1)}\n"
            f"Dispatch mode: {workflow.get('dispatch_mode', 'graph')}\n"
            f"Main route: {' -> '.join(self._stage_label(item) for item in route) or 'not configured'}\n"
            f"Direct edges: {len(workflow.get('edges') or [])}\n"
            f"Conditional edges: {len(workflow.get('conditional_edges') or [])}"
        )
        return {
            "type": "report",
            "message": message,
            "workflow": workflow,
            "source": self.skill_name,
            "channel": "promotion_ui",
        }

    def _format_leader_status(self, leader: dict[str, Any]) -> dict[str, Any]:
        metrics = leader.get("metrics") or {}
        management_scope = leader.get("management_scope") or {}
        org_profile = leader.get("organization_profile") or {}
        message = (
            f"{leader.get('display_name', leader.get('name'))} status:\n"
            f"Identifier: {leader.get('name')}\n"
            f"Lifecycle: {leader.get('status')}\n"
            f"Version: v{leader.get('version', 1)}\n"
            f"Success rate: {self._percent(metrics.get('success_rate', 0.0))}\n"
            f"Average tokens: {metrics.get('avg_tokens', 0)}\n"
            f"Token budget: {leader.get('token_limit', 0)}\n"
            f"Pending config actions: {leader.get('pending_config_actions', 0)}"
        )
        if org_profile:
            message += (
                f"\nExecutive title: {org_profile.get('executive_title', '-')}"
                f"\nDepartment center: {org_profile.get('department_name', '-')}"
                f"\nTitle code: {org_profile.get('title_code', '-')}"
            )
        if management_scope:
            message += (
                f"\nDirect governance: {'yes' if management_scope.get('direct_ceo_managed') else 'no'}"
                f"\nIn production main route: {'yes' if management_scope.get('in_main_workflow_route') else 'no'}"
                f"\nUser-facing department: {'yes' if management_scope.get('user_facing') else 'no'}"
            )
        return {
            "type": "report",
            "message": message,
            "leader": leader,
            "source": self.skill_name,
            "channel": "promotion_ui",
        }

    def _format_evolution_report(self, evolution: dict[str, Any]) -> dict[str, Any]:
        actions = evolution.get("issued_config_actions") or evolution.get("company_status", {}).get("issued_config_actions") or []
        message = (
            "Governance evolution cycle completed:\n"
            f"Evolution: {'enabled' if evolution.get('evolution_enabled') else 'disabled'}\n"
            f"New config actions: {len(actions)}\n"
            f"Message: {evolution.get('message') or 'The observe-analyze-decide loop completed.'}"
        )
        return {
            "type": "report",
            "message": message,
            "evolution": evolution,
            "source": self.skill_name,
            "channel": "promotion_ui",
        }

    def _format_error(self, message: str) -> dict[str, Any]:
        return {
            "type": "error",
            "message": message,
            "source": self.skill_name,
            "channel": "promotion_ui",
        }

    def _format_reply(self, message: str) -> dict[str, Any]:
        return {
            "type": "reply",
            "message": message,
            "source": self.skill_name,
            "channel": "promotion_ui",
        }

    def _percent(self, value: Any) -> str:
        return f"{float(value or 0.0) * 100:.1f}%"

    def _stage_label(self, stage_name: str) -> str:
        return self.STAGE_LABELS.get(stage_name, stage_name)
