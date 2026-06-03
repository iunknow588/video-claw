from __future__ import annotations

import hashlib
import json


class PromptVersionSkill:
    skill_name = "lead.research_development.prompt_version"

    def run(self, input_bundle: dict) -> dict:
        prompt_bundle = dict(input_bundle.get("prompt_bundle") or {})
        canonical_payload = {
            key: prompt_bundle.get(key)
            for key in sorted(prompt_bundle)
            if key != "trace_id"
        }
        fingerprint = hashlib.sha1(
            json.dumps(canonical_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:12]
        version = 1
        version_label = f"prompt:v{version}:{fingerprint[:8]}"
        return {
            "version": version,
            "version_label": version_label,
            "fingerprint": fingerprint,
            "quality_score": float(input_bundle.get("quality_score", 0.0) or 0.0),
            "warnings": list(input_bundle.get("warnings") or []),
            "issues": list(input_bundle.get("issues") or []),
            "prompt_bundle": prompt_bundle,
        }
