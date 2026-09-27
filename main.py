import argparse
import uvicorn
from app.monitoring.dashboard.main import dashboard_app

def run_backtest():
    print("Running backtest...")

from app.config.settings import settings
from app.execution.mt5_adapter import MT5Adapter
from app.strategies.engine import StrategyEngine
from app.ai.brain import AIBrain
import time

def run_trading_loop(is_live: bool = False):
    print(f"Starting {'LIVE' if is_live else 'PAPER'} trading engine on {settings.DEFAULT_SYMBOL}...")
    adapter = MT5Adapter()
    if not adapter.connect():
        print("Failed to connect to MT5.")
        return

    strategy = StrategyEngine()
    ai = AIBrain(settings.AI_MODEL_NAME)

    # Simulate a single loop iteration for demonstration
    print("Fetching market data...")
    data = adapter.fetch_ohlcv(settings.DEFAULT_SYMBOL, "1H")

    print("Evaluating strategies...")
    candidates = strategy.evaluate_market_data(data)

    print("AI evaluating candidates...")
    decision = ai.evaluate_candidates(candidates, {})

    print(f"AI Decision: {decision}")

    if decision.get("action") in ["BUY", "SELL"]:
        order = {
            "symbol": settings.DEFAULT_SYMBOL,
            "side": decision["action"],
            "quantity": 0.1 # Example quantity
        }
        print(f"Submitting order: {order}")
        result = adapter.submit_order(order)
        print(f"Order result: {result}")

def run_paper_trading():
    run_trading_loop(is_live=False)

def run_live_trading():
    print("WARNING: Live trading requires explicit operator activation!")
    run_trading_loop(is_live=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous AI Trading System")
    parser.add_argument("--mode", type=str, choices=["dashboard", "backtest", "paper", "live", "replay", "shadow"], default="dashboard")
    args = parser.parse_args()

    if args.mode == "dashboard":
        print("Starting monitoring dashboard...")
        uvicorn.run(dashboard_app, host="127.0.0.1", port=8000)
    elif args.mode == "backtest":
        run_backtest()
    elif args.mode == "paper":
        run_paper_trading()
    elif args.mode == "live":
        run_live_trading()
    else:
        print(f"Mode {args.mode} not yet fully implemented.")
