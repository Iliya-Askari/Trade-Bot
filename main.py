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

def log_trade(symbol: str, direction: str, quantity: float, status: str, entry_price: float = 0.0, stop_loss: float = None, take_profit: float = None):
    db = SessionLocal()
    try:
        trade = Trade(
            trade_id=str(uuid.uuid4()),
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            status=status,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        db.add(trade)
        db.commit()
    except Exception as e:
        print(f"Failed to log trade: {e}")
    finally:
        db.close()

def has_open_position(symbol: str, direction: str) -> bool:
    db = SessionLocal()
    try:
        count = db.query(Trade).filter(Trade.status == "OPEN", Trade.symbol == symbol, Trade.direction == direction).count()
        return count > 0
    except Exception as e:
        log_event("ERROR", "PositionManager", f"Failed to check open positions: {e}")
        return False
    finally:
        db.close()

def manage_open_positions(current_price: float, data: list, strategy: StrategyEngine, adapter: MT5Adapter):
    db = SessionLocal()
    try:
        open_trades = db.query(Trade).filter(Trade.status == "OPEN").all()
        for trade in open_trades:
            close_trade = False
            pnl = 0.0

            # 1. Dynamic Early Exit check
            early_exit = strategy.check_early_exit(data, trade.direction)
            if early_exit:
                close_trade = True
                log_event("WARNING", "PositionManager", f"DYNAMIC EARLY EXIT triggered for {trade.direction} {trade.symbol}. Trend reversed.")

            # 2. Hard Stop/Take Profit check
            if trade.direction == "LONG":
                if not close_trade and trade.stop_loss and current_price <= trade.stop_loss:
                    close_trade = True
                    log_event("WARNING", "PositionManager", f"Stop Loss hit for LONG {trade.symbol} at {current_price}")
                elif not close_trade and trade.take_profit and current_price >= trade.take_profit:
                    close_trade = True
                    log_event("INFO", "PositionManager", f"Take Profit hit for LONG {trade.symbol} at {current_price}")

                if close_trade:
                    pnl = (current_price - trade.entry_price) * trade.quantity

            elif trade.direction == "SHORT":
                if not close_trade and trade.stop_loss and current_price >= trade.stop_loss:
                    close_trade = True
                    log_event("WARNING", "PositionManager", f"Stop Loss hit for SHORT {trade.symbol} at {current_price}")
                elif not close_trade and trade.take_profit and current_price <= trade.take_profit:
                    close_trade = True
                    log_event("INFO", "PositionManager", f"Take Profit hit for SHORT {trade.symbol} at {current_price}")

                if close_trade:
                    pnl = (trade.entry_price - current_price) * trade.quantity

            if close_trade:
                # Transmit CLOSE order to broker
                close_res = adapter.close_position(symbol=trade.symbol, position_id=trade.trade_id, side=trade.direction, volume=trade.quantity)

                if close_res.get("status") == "CLOSED":
                    trade.status = "CLOSED"
                    trade.exit_price = current_price
                    trade.pnl = pnl
                    db.commit()
                    log_event("INFO", "PositionManager", f"Trade {trade.trade_id} closed on broker. PnL: ${pnl:.2f}")
                else:
                    log_event("ERROR", "PositionManager", f"Failed to close trade {trade.trade_id} on broker: {close_res}")
    except Exception as e:
        log_event("ERROR", "PositionManager", f"Failed to manage positions: {e}")
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

    loop_count = 0
    last_candle_time = None

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
            if not data:
                continue

            current_price = data[-1]['close']
            current_candle_time = data[-1]['time']

            # 1. Manage existing positions with dynamic early exit logic
            manage_open_positions(current_price, data, strategy, adapter)

            # Periodic scan logging to show activity
            loop_count += 1
            if loop_count % 5 == 0:
                log_event("INFO", "TradingLoop", f"Scanning {settings.DEFAULT_SYMBOL} at ${current_price:.2f}...")

            # 2. Look for new setups ONLY on new candle
            if last_candle_time is None or current_candle_time != last_candle_time:
                candidates = strategy.evaluate_market_data(data)

                if candidates.get("status") in ["NO_DATA", "WAIT", "NO_TRADE"]:
                    # Suppress spammy wait logs
                    pass
                else:
                    # Update last candle time only if we successfully evaluated a new candle
                    last_candle_time = current_candle_time
                    log_event("INFO", "Strategy", f"Signal: {candidates.get('direction')} | {candidates.get('reason')}")

                    direction = candidates.get('direction')

                    # 3. Position Manager Check (Prevent duplicate orders)
                    if has_open_position(settings.DEFAULT_SYMBOL, direction):
                        log_event("INFO", "PositionManager", f"Existing {direction} position open for {settings.DEFAULT_SYMBOL}: NO_TRADE")
                        continue

                    decision = ai.evaluate_candidates(candidates, {})

                    if decision.get("action") == "NO_TRADE":
                        log_event("INFO", "AI", f"Decision: NO_TRADE | Reason: {decision.get('reasoning_summary')}")
                    elif decision.get("action") in ["BUY", "SELL"]:
                        log_event("INFO", "AI", f"Decision: {decision.get('action')} | Confidence: {decision.get('confidence'):.2f}")
                    trade_proposal = {
                        "risk_percent": settings.MAX_RISK_PER_TRADE,
                        "leverage": settings.MAX_LEVERAGE,
                        "symbol": settings.DEFAULT_SYMBOL,
                        "side": decision["action"]
                    }

                    # ENFORCE RISK ENGINE
                    if not risk_engine.validate_trade(trade_proposal, account_state={"daily_loss": 0, "drawdown": 0}):
                        log_event("WARNING", "RiskEngine", f"Trade rejected by Risk Engine: {trade_proposal}")
                        continue

                    # Calculate quantity based on UI Allocation and Leverage
                    # Note: Assumes base currency calculation logic. Simply using dollars for prototype.
                    quantity = round((settings.TRADE_ALLOCATION * settings.MAX_LEVERAGE) / current_price, 2)
                    sl = candidates.get("stop_loss")
                    tp = candidates.get("take_profit")

                    log_event("INFO", "Risk", f"Risk: {settings.MAX_RISK_PER_TRADE*100}% | Position: {quantity} | SL: {sl:.2f} | TP: {tp:.2f}")

                    order = {
                        "symbol": settings.DEFAULT_SYMBOL,
                        "side": decision["action"],
                        "quantity": quantity,
                        "price": candidates.get("entry_price", current_price),
                        "stop_loss": sl,
                        "take_profit": tp
                    }
                    log_event("INFO", "Execution", f"Submitting {decision['action']} {quantity} {settings.DEFAULT_SYMBOL}")
                    result = adapter.submit_order(order)
                    log_event("INFO", "Execution", f"{result.get('status')} - ID: {result.get('order_id', 'N/A')}")

                    if result.get("status") in ["SUBMITTED", "FILLED"]:
                        # Handle mock vs live order IDs
                        final_order_id = result.get("order_id", str(uuid.uuid4()))

                        db = SessionLocal()
                        try:
                            trade = Trade(
                                trade_id=final_order_id,
                                symbol=settings.DEFAULT_SYMBOL,
                                direction=decision["action"],
                                quantity=round(quantity, 2),
                                status="OPEN",
                                entry_price=candidates.get("entry_price", current_price),
                                stop_loss=candidates.get("stop_loss"),
                                take_profit=candidates.get("take_profit")
                            )
                            db.add(trade)
                            db.commit()
                        except Exception as e:
                            log_event("ERROR", "Execution", f"Failed to log trade to DB: {e}")
                        finally:
                            db.close()

            # Sleep to prevent spamming the CPU/API
            time.sleep(5)

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
