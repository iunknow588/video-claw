from __future__ import annotations

from departments.CIO.models.analysis import AnalysisReport
from departments.CIO.schemas.video import DomainWorkflowRequest


class VideoProductionUseCase:
    """COO use case for script generation, media assembly, render execution, and asset landing."""

    def __init__(self, assembly) -> None:
        self.assembly = assembly

    async def execute(
        self,
        *,
        trace_id: str,
        request: DomainWorkflowRequest,
        planning_bundle: dict,
        primary_analysis: AnalysisReport,
        qa_feedback: str | None = None,
    ) -> dict:
        topic = planning_bundle["prompt_bundle"]["script_topic"]
        if qa_feedback:
            topic = f"{topic} | QA修正：{qa_feedback[:80]}"

        script = await self.assembly.script_service.generate_script(
            analysis=primary_analysis,
            content_type=request.content_type,
            style=request.style,
            topic=topic,
            duration=request.duration,
        )
        script_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.production",
                skill=self.assembly.get_skill("lead.production.script_draft"),
                input_bundle={"trace_id": trace_id, "script": self.assembly.serialize_script(script)},
            )
        ).output_json
        material_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.research",
                skill=self.assembly.get_skill("lead.research.material_search"),
                input_bundle={
                    "trace_id": trace_id,
                    "platform": request.platform,
                    "target_duration": request.duration,
                    "search_terms": list(planning_bundle["prompt_bundle"].get("visual_keywords", [])),
                    "scenes": list(script.scenes or []),
                },
            )
        ).output_json
        subtitle_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.production",
                skill=self.assembly.get_skill("lead.production.subtitle_compose"),
                input_bundle={
                    "trace_id": trace_id,
                    "script": self.assembly.serialize_script(script),
                    "target_duration": request.duration,
                },
            )
        ).output_json
        voiceover_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.production",
                skill=self.assembly.get_skill("lead.production.voiceover_generate"),
                input_bundle={
                    "trace_id": trace_id,
                    "script": self.assembly.serialize_script(script),
                    "target_duration": request.duration,
                    "voice_profile": "narrator-neutral",
                },
            )
        ).output_json

        workflow_notes: list[str] = []
        if request.auto_approve_script:
            script = await self.assembly.script_service.review_script(script.uuid, True, "Auto-approved by workflow.")
            script_bundle = (
                await self.assembly.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.production",
                    skill=self.assembly.get_skill("lead.production.script_review"),
                    input_bundle={"trace_id": trace_id, "script": self.assembly.serialize_script(script)},
                )
            ).output_json
            workflow_notes.append("script_approved")

        video_task = None
        if request.auto_generate_video:
            if script.status != "approved":
                workflow_notes.append("video_skipped_unapproved_script")
            else:
                video_task = await self.assembly.video_service.create_task(
                    script=script,
                    style=request.video_style or request.style,
                )
                video_task = await self.assembly.video_service.process_task(video_task.uuid)
                video_task_bundle = (
                    await self.assembly.recorder.call_skill(
                        trace_id=trace_id,
                        parent_id="lead.production",
                        skill=self.assembly.get_skill("lead.production.video_task"),
                        input_bundle={"trace_id": trace_id, "video_task": self.assembly.serialize_video_task(video_task)},
                    )
                ).output_json
                processed_bundle = (
                    await self.assembly.recorder.call_skill(
                        trace_id=trace_id,
                        parent_id="lead.production",
                        skill=self.assembly.get_skill("lead.production.video_process"),
                        input_bundle={"trace_id": trace_id, **video_task_bundle},
                    )
                ).output_json
                review_bundle = (
                    await self.assembly.recorder.call_skill(
                        trace_id=trace_id,
                        parent_id="lead.production",
                        skill=self.assembly.get_skill("lead.production.video_review"),
                        input_bundle={"trace_id": trace_id, **processed_bundle},
                    )
                ).output_json
                await self.assembly.recorder.call_skill(
                    trace_id=trace_id,
                    parent_id="lead.production",
                    skill=self.assembly.get_skill("lead.production.asset_storage"),
                    input_bundle={
                        "trace_id": trace_id,
                        **review_bundle,
                        "video_bundle": {
                            "subtitle_bundle": subtitle_bundle,
                            "voiceover_bundle": voiceover_bundle,
                            "material_bundle": material_bundle,
                        },
                    },
                )
                workflow_notes.append("video_generated")
        else:
            workflow_notes.append("video_not_requested")

        composition_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.production",
                skill=self.assembly.get_skill("lead.production.video_compose_plan"),
                input_bundle={
                    "platform": request.platform,
                    "script": self.assembly.serialize_script(script),
                    "material_bundle": material_bundle,
                    "subtitle_bundle": subtitle_bundle,
                    "voiceover_bundle": voiceover_bundle,
                    "video_task": self.assembly.serialize_video_task(video_task) if video_task else None,
                },
            )
        ).output_json
        render_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.production",
                skill=self.assembly.get_skill("lead.production.render_execute"),
                input_bundle={
                    "trace_id": trace_id,
                    "platform": request.platform,
                    "duration": request.duration,
                    "composition_bundle": composition_bundle,
                    "video_task": self.assembly.serialize_video_task(video_task) if video_task else None,
                },
            )
        ).output_json
        await self.assembly.recorder.call_skill(
            trace_id=trace_id,
            parent_id="lead.production",
            skill=self.assembly.get_skill("lead.production.asset_storage"),
            input_bundle={
                "trace_id": trace_id,
                "video_bundle": {
                    "subtitle_bundle": subtitle_bundle,
                    "voiceover_bundle": voiceover_bundle,
                    "material_bundle": material_bundle,
                    "composition_bundle": composition_bundle,
                    "render_bundle": render_bundle,
                },
            },
        )

        if render_bundle.get("render_mode") == "ffmpeg_preview":
            workflow_notes.append("scene_preview_rendered")
        elif render_bundle.get("render_mode") == "preview_placeholder":
            workflow_notes.append("placeholder_preview_rendered")
        if qa_feedback:
            workflow_notes.append("qa_rework_requested")

        production_bundle = {
            "script": script,
            "video_task": video_task,
            "script_bundle": script_bundle,
            "material_bundle": material_bundle,
            "subtitle_bundle": subtitle_bundle,
            "voiceover_bundle": voiceover_bundle,
            "composition_bundle": composition_bundle,
            "render_bundle": render_bundle,
            "qa_feedback": qa_feedback,
            "notes": workflow_notes,
        }
        retry_bundle = (
            await self.assembly.recorder.call_skill(
                trace_id=trace_id,
                parent_id="lead.production",
                skill=self.assembly.get_skill("lead.production.retry_recovery"),
                input_bundle={"trace_id": trace_id, **production_bundle},
            )
        ).output_json
        if retry_bundle.get("retry"):
            workflow_notes.append("production_retry_requested")

        return {
            "script": script,
            "video_task": video_task,
            "trace_bundle": {
                "script": self.assembly.serialize_script(script),
                "video_task": self.assembly.serialize_video_task(video_task) if video_task else None,
                "script_bundle": script_bundle,
                "material_bundle": material_bundle,
                "subtitle_bundle": subtitle_bundle,
                "voiceover_bundle": voiceover_bundle,
                "composition_bundle": composition_bundle,
                "render_bundle": render_bundle,
                "qa_feedback": qa_feedback,
                "notes": workflow_notes,
            },
            "bundle": production_bundle,
            "notes": workflow_notes,
        }
