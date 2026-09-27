import argparse
import uvicorn
from app.monitoring.dashboard.main import dashboard_app

def run_backtest():
    print("Running backtest...")

def run_paper_trading():
    print("Starting paper trading engine...")

def run_live_trading():
    print("WARNING: Live trading requires explicit operator activation!")
    print("Starting live trading engine...")

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
