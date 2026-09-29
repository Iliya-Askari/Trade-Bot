import argparse
import uvicorn
from app.monitoring.dashboard.main import dashboard_app

def run_backtest():
    print("Running backtest...")

from app.config.settings import settings
from app.execution.mt5_adapter import MT5Adapter
from app.strategies.engine import StrategyEngine
from app.ai.brain import AIBrain
from app.risk.engine import RiskEngine
from app.database.session import SessionLocal
from app.database.models import SystemEvent, Trade
import time
import uuid

def log_event(level: str, module: str, message: str):
    print(f"[{level}] {module}: {message}")
    db = SessionLocal()
    try:
        event = SystemEvent(level=level, module=module, message=message)
        db.add(event)
        db.commit()
    except Exception as e:
        print(f"Failed to log event: {e}")
    finally:
        db.close()

def log_trade(symbol: str, direction: str, quantity: float, status: str, entry_price: float = 0.0):
    db = SessionLocal()
    try:
        trade = Trade(
            trade_id=str(uuid.uuid4()),
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            status=status,
            entry_price=entry_price
        )
        db.add(trade)
        db.commit()
    except Exception as e:
        print(f"Failed to log trade: {e}")
    finally:
        db.close()

import threading
from app.monitoring.dashboard.main import trading_state

def run_trading_loop():
    log_event("INFO", "TradingLoop", f"Background thread spawned for {settings.DEFAULT_SYMBOL}...")

    adapter = MT5Adapter()
    strategy = StrategyEngine()
    ai = AIBrain(settings.AI_MODEL_NAME)
    risk_engine = RiskEngine()

    log_event("INFO", "TradingLoop", "Ready. Waiting for START signal from UI.")

    while True:
        try:
            time.sleep(2) # check interval
            if not trading_state.get("active", False):
                continue

            if not adapter.connect():
                log_event("ERROR", "MT5Adapter", "Failed to connect to MT5. Check credentials in Settings.")
                trading_state["active"] = False
                continue

            data = adapter.fetch_ohlcv(settings.DEFAULT_SYMBOL, "1H")

            candidates = strategy.evaluate_market_data(data)

            if candidates.get("status") in ["NO_DATA", "WAIT", "NO_TRADE"]:
                # Suppress spammy wait logs, but print to console
                print(f"Waiting... {candidates.get('reason', '')}")
            else:
                log_event("INFO", "Strategy", f"Signal found: {candidates.get('direction')} - {candidates.get('reason')}")

                decision = ai.evaluate_candidates(candidates, {})
                log_event("INFO", "AI", f"Decision: {decision.get('action')} (Confidence: {decision.get('confidence')})")

                if decision.get("action") in ["BUY", "SELL"]:
                    trade_proposal = {
                        "risk_percent": settings.MAX_RISK_PER_TRADE,
                        "leverage": 1.0,
                        "symbol": settings.DEFAULT_SYMBOL,
                        "side": decision["action"]
                    }

                    # ENFORCE RISK ENGINE
                    if not risk_engine.validate_trade(trade_proposal, account_state={"daily_loss": 0, "drawdown": 0}):
                        log_event("WARNING", "RiskEngine", f"Trade rejected by Risk Engine: {trade_proposal}")
                        continue

                    order = {
                        "symbol": settings.DEFAULT_SYMBOL,
                        "side": decision["action"],
                        "quantity": 0.1
                    }
                    log_event("INFO", "Execution", f"Submitting order: {order}")
                    result = adapter.submit_order(order)
                    log_event("INFO", "Execution", f"Order result: {result}")

                    if result.get("status") in ["SUBMITTED", "FILLED"]:
                        log_trade(
                            symbol=settings.DEFAULT_SYMBOL,
                            direction=decision["action"],
                            quantity=0.1,
                            status="OPEN"
                        )

            # Sleep to prevent spamming the CPU/API
            time.sleep(10)

        except KeyboardInterrupt:
            log_event("INFO", "TradingLoop", "Trading loop stopped by operator.")
            break
        except Exception as e:
            log_event("ERROR", "TradingLoop", f"Exception in trading loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous AI Trading System")
    parser.add_argument("--mode", type=str, choices=["dashboard", "backtest", "paper", "live", "replay", "shadow"], default="dashboard")
    args = parser.parse_args()

    if args.mode == "dashboard":
        print("Starting monitoring dashboard & Background Trading Thread...")

        # Start trading thread in background
        t = threading.Thread(target=run_trading_loop, daemon=True)
        t.start()

        # Start FastAPI
        uvicorn.run(dashboard_app, host="127.0.0.1", port=8000)
    elif args.mode == "backtest":
        run_backtest()
    else:
        print(f"Mode {args.mode} is now managed via the dashboard UI.")
