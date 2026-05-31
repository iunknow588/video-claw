from __future__ import annotations


class RetryRecoverySkill:
    skill_name = "lead.production.retry_recovery"

    def run(self, input_bundle: dict) -> dict:
        return {"retry": False, "bundle": input_bundle}

