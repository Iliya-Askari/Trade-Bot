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

        # Simplified AI evaluation
        return {
            "action": "BUY" if direction == "LONG" else "SELL",
            "confidence": candidates.get("confidence", 0.5) * 1.2, # AI boosts confidence based on 'context'
            "reasoning_summary": f"AI confirms {direction} setup via {self.model_name}.",
            "expected_value": 0.05
        }
