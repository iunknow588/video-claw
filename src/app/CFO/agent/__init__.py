from app.CFO.leader import FinanceLeader
from app.CFO.skills import ChargeSkill, EstimateCostSkill, VerifyBalanceSkill


class CFOAgent:
    """Canonical CFO agent facade: finance leader plus managed skill nodes."""

    leader_class = FinanceLeader
    managed_skill_classes = (EstimateCostSkill, VerifyBalanceSkill, ChargeSkill)
    department_domain = "finance_gate"

