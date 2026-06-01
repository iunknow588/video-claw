from __future__ import annotations


class AssetStorageSkill:
    skill_name = "lead.production.asset_storage"

    def run(self, input_bundle: dict) -> dict:
        video_bundle = input_bundle.get("video_bundle") or input_bundle
        subtitle_bundle = video_bundle.get("subtitle_bundle") or {}
        voiceover_bundle = video_bundle.get("voiceover_bundle") or {}
        material_bundle = video_bundle.get("material_bundle") or {}
        composition_bundle = video_bundle.get("composition_bundle") or {}
        render_bundle = video_bundle.get("render_bundle") or {}
        asset_manifest = {
            "subtitle_file": subtitle_bundle.get("subtitle_file"),
            "audio_file": voiceover_bundle.get("audio_file"),
            "material_cache_root": material_bundle.get("cache_root"),
            "composition_inputs": ((composition_bundle.get("ffmpeg_plan") or {}).get("inputs") or []),
            "render_manifest_path": render_bundle.get("render_manifest_path"),
            "delivery_asset_url": render_bundle.get("delivery_asset_url"),
            "local_render_path": render_bundle.get("local_render_path"),
        }
        return {"asset_ref": "storage://production-assets", "asset_manifest": asset_manifest, "video_bundle": input_bundle}
