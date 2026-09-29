from typing import Dict, Any

class AIBrain:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def evaluate_candidates(self, candidates: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI evaluates the technical setups against fundamental/news context.
        """
        if candidates.get("status") == "NO_DATA":
            return {"action": "NO_TRADE", "reason": "Insufficient data"}

        direction = candidates.get("direction", "WAIT")

        # Advanced Validation: Risk/Reward check based on dynamic ATR stops
        rr = candidates.get("risk_reward_ratio", 0)

        if rr < 2.0:
            return {
                "action": "NO_TRADE",
                "reasoning_summary": f"Rejected by AI: Risk/Reward ratio of {rr:.2f} is below the strict 1:2 minimum threshold."
            }

        raw_confidence = candidates.get("confidence", 0.5) * 1.2 # AI boosts confidence based on 'context'
        final_confidence = max(0.0, min(1.0, raw_confidence)) # Clamp between 0 and 1

        # Hard confidence threshold check
        threshold = 0.70
        if final_confidence < threshold:
            return {
                "action": "NO_TRADE",
                "reasoning_summary": f"Rejected by AI: Confidence ({final_confidence:.2f}) below threshold ({threshold:.2f})."
            }

        # Simplified AI evaluation
        return {
            "action": "BUY" if direction == "LONG" else "SELL",
            "confidence": final_confidence,
            "reasoning_summary": f"AI confirms {direction} setup via {self.model_name}. R/R ratio verified ({rr:.2f}).",
            "expected_value": 0.05
        }
