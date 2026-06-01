from __future__ import annotations


class TitleCandidateSkill:
    skill_name = "lead.research_development.title_candidate"

    def run(self, input_bundle: dict) -> dict:
        return {"title_candidates": input_bundle.get("title_candidates", [])}

