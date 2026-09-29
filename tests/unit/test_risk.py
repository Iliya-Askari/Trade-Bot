from app.risk.engine import RiskEngine
from app.config.settings import settings

def test_risk_engine_validates_acceptable_trade():
    engine = RiskEngine()

    # Mock settings values via global settings object since RiskEngine now reads dynamically
    settings.MAX_RISK_PER_TRADE = 0.01
    settings.MAX_DAILY_LOSS = 0.05
    settings.MAX_DRAWDOWN = 0.10
    settings.MAX_LEVERAGE = 1.0

    trade_proposal = {
        "risk_percent": 0.005,
        "leverage": 1.0
    }

    account_state = {
        "daily_loss": 0.01,
        "drawdown": 0.02
    }

    is_valid, reason = engine.validate_trade(trade_proposal, account_state)
    assert is_valid is True

def test_risk_engine_rejects_excessive_risk():
    engine = RiskEngine()
    settings.MAX_RISK_PER_TRADE = 0.01

    trade_proposal = {"risk_percent": 0.02, "leverage": 1.0}
    account_state = {"daily_loss": 0, "drawdown": 0}

    is_valid, reason = engine.validate_trade(trade_proposal, account_state)
    assert is_valid is False
    assert "Proposed risk" in reason

def test_risk_engine_rejects_max_drawdown():
    engine = RiskEngine()
    settings.MAX_DRAWDOWN = 0.10

    trade_proposal = {"risk_percent": 0.005, "leverage": 1.0}
    account_state = {"daily_loss": 0, "drawdown": 0.15}  # Drawdown exceeded

    is_valid, reason = engine.validate_trade(trade_proposal, account_state)
    assert is_valid is False
    assert "Drawdown" in reason
