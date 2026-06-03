from __future__ import annotations


class TitleCandidateSkill:
    skill_name = "lead.research_development.title_candidate"

    def run(self, input_bundle: dict) -> dict:
        candidates = []
        for value in input_bundle.get("title_candidates", []):
            text = str(value or "").strip()
            if text and text not in candidates:
                candidates.append(text)

        script_topic = str(input_bundle.get("script_topic") or "").strip()
        if script_topic and script_topic not in candidates:
            candidates.insert(0, script_topic)

        for value in input_bundle.get("script_topic_variants", []):
            text = str(value or "").strip()
            if text and text not in candidates:
                candidates.append(text)

        return {"title_candidates": candidates[:6]}
