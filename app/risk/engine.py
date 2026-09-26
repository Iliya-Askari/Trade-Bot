from typing import Dict, Any
from app.config.settings import settings

class RiskEngine:
    def __init__(self):
        self.max_risk_per_trade = settings.MAX_RISK_PER_TRADE
        self.max_daily_loss = settings.MAX_DAILY_LOSS
        self.max_drawdown = settings.MAX_DRAWDOWN
        self.max_leverage = settings.MAX_LEVERAGE

    def validate_trade(self, trade_proposal: Dict[str, Any], account_state: Dict[str, Any]) -> bool:
        """
        Independent, deterministic, authoritative risk check.
        Returns True if trade is approved, False otherwise.
        """
        # Basic deterministic checks
        if account_state.get("daily_loss", 0) >= self.max_daily_loss:
            return False

        if account_state.get("drawdown", 0) >= self.max_drawdown:
            return False

        proposed_risk = trade_proposal.get("risk_percent", 0)
        if proposed_risk > self.max_risk_per_trade:
            return False

        proposed_leverage = trade_proposal.get("leverage", 1.0)
        if proposed_leverage > self.max_leverage:
            return False

        return True
