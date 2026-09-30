import pytest

def test_no_trade_guard_respects_ai_rejection():
    # In main.py, the trading loop executes:
    # decision = ai.evaluate_candidates(candidates, {})
    # if decision.get("action") == "NO_TRADE": continue
    #
    # We will test the AIBrain output directly to ensure it can explicitly emit NO_TRADE

    from app.ai.brain import AIBrain
    brain = AIBrain("dummy")

    # Test 1: Confidence below threshold
    candidates_low_conf = {
        "status": "CANDIDATE",
        "direction": "LONG",
        "entry_price": 1.1000,
        "stop_loss": 1.0900,
        "take_profit": 1.1200,
        "confidence": 0.3,  # Below 0.70 threshold (0.3 * 1.2 = 0.36)
        "risk_reward_ratio": 2.5 # Avoid RR rejection
    }

    decision_low = brain.evaluate_candidates(candidates_low_conf, {})
    assert decision_low["action"] == "NO_TRADE"
    assert "Confidence" in decision_low["reasoning_summary"]

    # Test 2: Invalid Risk/Reward
    candidates_bad_rr = {
        "status": "CANDIDATE",
        "direction": "LONG",
        "entry_price": 1.1000,
        "stop_loss": 1.0900,
        "take_profit": 1.1100,
        "confidence": 0.8,
        "risk_reward_ratio": 1.0
    }

    decision_rr = brain.evaluate_candidates(candidates_bad_rr, {})
    assert decision_rr["action"] == "NO_TRADE"
    assert "Risk/Reward ratio" in decision_rr["reasoning_summary"]
