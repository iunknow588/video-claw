from __future__ import annotations


class EmotionCurveSkill:
    skill_name = "lead.analysis.emotion_curve"

    def run(self, input_bundle: dict) -> dict:
        return {
            **input_bundle,
            "emotion_curve": input_bundle.get("emotion_curve", {}),
        }
