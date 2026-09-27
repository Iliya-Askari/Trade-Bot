from app.risk.engine import RiskEngine

def test_risk_engine_validates_acceptable_trade():
    engine = RiskEngine()

    # Mock settings values (e.g. max_risk_per_trade = 0.01)
    engine.max_risk_per_trade = 0.01
    engine.max_daily_loss = 0.05
    engine.max_drawdown = 0.10
    engine.max_leverage = 1.0

    trade_proposal = {
        "risk_percent": 0.005,
        "leverage": 1.0
    }

    account_state = {
        "daily_loss": 0.01,
        "drawdown": 0.02
    }

    assert engine.validate_trade(trade_proposal, account_state) is True

def test_risk_engine_rejects_excessive_risk():
    engine = RiskEngine()
    engine.max_risk_per_trade = 0.01

    trade_proposal = {"risk_percent": 0.02, "leverage": 1.0}
    account_state = {"daily_loss": 0, "drawdown": 0}

    assert engine.validate_trade(trade_proposal, account_state) is False

def test_risk_engine_rejects_max_drawdown():
    engine = RiskEngine()
    engine.max_drawdown = 0.10

    trade_proposal = {"risk_percent": 0.005, "leverage": 1.0}
    account_state = {"daily_loss": 0, "drawdown": 0.15}  # Drawdown exceeded

    assert engine.validate_trade(trade_proposal, account_state) is False
