from typing import Dict, Any, List

class StrategyEngine:
    def __init__(self):
        self.active_strategies = ["Trend Following", "Mean Reversion"]

    def evaluate_market_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyzes market structure and generates potential setups.
        """
        if not data:
            return {"status": "NO_DATA"}

        latest = data[-1]

        # Extremely simplified logic for demonstration
        if latest.get("close", 0) > latest.get("open", 0):
            return {
                "symbol": "DEFAULT",
                "direction": "LONG",
                "confidence": 0.7,
                "strategy": "Trend Following"
            }
        else:
            return {
                "symbol": "DEFAULT",
                "direction": "SHORT",
                "confidence": 0.6,
                "strategy": "Mean Reversion"
            }
