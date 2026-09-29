from typing import Dict, Any, Tuple
from app.config.settings import settings

class RiskEngine:
    def __init__(self):
        # We don't cache settings here anymore, we read them dynamically
        # to ensure UI updates apply immediately.
        pass

    def validate_trade(self, trade_proposal: Dict[str, Any], account_state: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Independent, deterministic, authoritative risk check.
        Returns (True, "Approved") if trade is approved.
        Returns (False, "Reason") if rejected.
        """
        # Fetch fresh settings
        max_risk = settings.MAX_RISK_PER_TRADE
        max_loss = settings.MAX_DAILY_LOSS
        max_dd = settings.MAX_DRAWDOWN
        max_lev = settings.MAX_LEVERAGE

        # Basic deterministic checks
        if account_state.get("daily_loss", 0) >= max_loss:
            return False, f"Daily loss ({account_state.get('daily_loss', 0)}) exceeds maximum allowed ({max_loss})"

        if account_state.get("drawdown", 0) >= max_dd:
            return False, f"Drawdown ({account_state.get('drawdown', 0)}) exceeds maximum allowed ({max_dd})"

        proposed_risk = trade_proposal.get("risk_percent", 0)
        if proposed_risk > max_risk:
            return False, f"Proposed risk ({proposed_risk}) exceeds maximum risk per trade ({max_risk})"

        proposed_leverage = trade_proposal.get("leverage", 1.0)
        if proposed_leverage > max_lev:
            return False, f"Proposed leverage ({proposed_leverage}) exceeds maximum allowed leverage ({max_lev})"

        return True, "Approved"
