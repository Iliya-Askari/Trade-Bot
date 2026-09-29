import argparse
import uvicorn
from app.monitoring.dashboard.main import dashboard_app

def run_backtest():
    print("Running backtest...")

from app.config.settings import settings
from app.execution.mt5_adapter import MT5Adapter
from app.strategies.engine import StrategyEngine
from app.ai.brain import AIBrain
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

def run_trading_loop(is_live: bool = False):
    mode = 'LIVE' if is_live else 'PAPER'
    log_event("INFO", "TradingLoop", f"Starting {mode} trading engine on {settings.DEFAULT_SYMBOL}...")

    adapter = MT5Adapter()
    if not adapter.connect():
        log_event("ERROR", "MT5Adapter", "Failed to connect to MT5.")
        return

    strategy = StrategyEngine()
    ai = AIBrain(settings.AI_MODEL_NAME)

    log_event("INFO", "TradingLoop", "Entering autonomous loop.")

    while True:
        try:
            # log_event("INFO", "TradingLoop", f"Analyzing {settings.DEFAULT_SYMBOL}...")
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
