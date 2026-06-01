from __future__ import annotations


class RetryRecoverySkill:
    skill_name = "lead.production.retry_recovery"

    def run(self, input_bundle: dict) -> dict:
        return {
            "retry": False,
            "retry_reason": None,
            "bundle": input_bundle,
        }


ProductionRetryRecoverySkill = RetryRecoverySkill

__all__ = ["ProductionRetryRecoverySkill", "RetryRecoverySkill"]
