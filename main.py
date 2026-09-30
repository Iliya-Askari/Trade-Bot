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

def has_open_position(symbol: str) -> bool:
    """Enforces ONE_POSITION_PER_SYMBOL policy regardless of direction."""
    db = SessionLocal()
    try:
        count = db.query(Trade).filter(Trade.status == "OPEN", Trade.symbol == symbol).count()
        return count > 0
    except Exception as e:
        log_event("ERROR", "PositionManager", f"Failed to check open positions: {e}")
        return False
    finally:
        db.close()

from app.database.models import AccountSnapshot
from datetime import datetime, timezone

def calculate_account_risk_state(adapter: MT5Adapter) -> dict:
    # Fail-Closed by default. If we can't determine risk, return None.
    if not adapter.mt5:
        # Mock mode safe defaults since there's no real broker risk
        return {"daily_loss": 0.0, "drawdown": 0.0}

    db = SessionLocal()
    try:
        acc_info = adapter.mt5.account_info()
        if not acc_info:
            log_event("ERROR", "RiskManager", "Could not fetch MT5 account info.")
            return None

        current_equity = acc_info.equity

        # Retrieve the latest snapshot to track peak equity and daily start equity
        snapshot = db.query(AccountSnapshot).order_by(AccountSnapshot.timestamp.desc()).first()
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        if snapshot is None or snapshot.timestamp.replace(tzinfo=timezone.utc) < today_start:
            # First run of the day, create a new snapshot
            new_snapshot = AccountSnapshot(
                day_start_equity=current_equity,
                peak_equity=current_equity
            )
            db.add(new_snapshot)
            db.commit()
            db.refresh(new_snapshot)
            snapshot = new_snapshot

        # Update peak equity if we hit a new high
        if current_equity > snapshot.peak_equity:
            snapshot.peak_equity = current_equity
            db.commit()

        peak_equity = snapshot.peak_equity
        daily_start_equity = snapshot.day_start_equity

        drawdown_pct = 0.0
        if peak_equity > 0:
            drawdown_pct = (peak_equity - current_equity) / peak_equity

        daily_loss_pct = 0.0
        if current_equity < daily_start_equity:
            daily_loss_pct = (daily_start_equity - current_equity) / daily_start_equity

        return {
            "daily_loss": daily_loss_pct,
            "drawdown": drawdown_pct,
            "equity": current_equity
        }
    except Exception as e:
        log_event("ERROR", "RiskManager", f"Failed to calculate account state: {e}")
        return None
    finally:
        db.close()

def manage_open_positions(current_price: float, data: list, strategy: StrategyEngine, adapter: MT5Adapter):
    db = SessionLocal()
    try:
        open_trades = db.query(Trade).filter(Trade.status == "OPEN").all()
        for trade in open_trades:

            # RECONCILIATION: Check if the broker already closed this position (e.g. SL/TP hit)
            pos_state = adapter.position_exists(trade.broker_position_id or trade.trade_id)

            if pos_state is None:
                log_event("WARNING", "Reconciliation", f"Broker position state UNKNOWN for {trade.trade_id}. Skipping management to prevent orphan trades.")
                continue

            if pos_state is False:
                log_event("WARNING", "Reconciliation", f"Trade {trade.trade_id} definitively missing on broker. Syncing local DB to CLOSED.")
                trade.status = "CLOSED"
                trade.exit_price = current_price # Approximate

                # Fetch EXACT PnL from MT5 history deals
                actual_pnl = 0.0
                if adapter.mt5 and settings.TRADING_MODE != "PAPER_TRADING":
                    from datetime import datetime, timedelta, timezone
                    trade.closed_at = datetime.now(timezone.utc)
                    pos_id = trade.broker_position_id or trade.trade_id
                    if pos_id and pos_id.isdigit():
                        deals = adapter.mt5.history_deals_get(position=int(pos_id))
                        if deals:
                            actual_pnl = sum([d.profit + d.commission + d.swap + d.fee for d in deals])

                trade.pnl = actual_pnl
                db.commit()
                log_event("INFO", "Reconciliation", f"Trade {trade.trade_id} synced. Actual PnL: ${actual_pnl:.2f}")
                continue

            close_trade = False
            pnl = 0.0

            contract_size = 100.0
            if adapter.mt5:
                symbol_info = adapter.mt5.symbol_info(trade.symbol)
                if symbol_info and symbol_info.trade_contract_size:
                    contract_size = symbol_info.trade_contract_size

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
                    pnl = (current_price - trade.entry_price) * trade.quantity * contract_size

            elif trade.direction == "SHORT":
                if not close_trade and trade.stop_loss and current_price >= trade.stop_loss:
                    close_trade = True
                    log_event("WARNING", "PositionManager", f"Stop Loss hit for SHORT {trade.symbol} at {current_price}")
                elif not close_trade and trade.take_profit and current_price <= trade.take_profit:
                    close_trade = True
                    log_event("INFO", "PositionManager", f"Take Profit hit for SHORT {trade.symbol} at {current_price}")

                if close_trade:
                    pnl = (trade.entry_price - current_price) * trade.quantity * contract_size

            if close_trade:
                # Transmit CLOSE order to broker
                # Use broker_position_id if it exists, otherwise fallback to trade_id (e.g. mock/paper IDs)
                # This ensures mapped orphan positions (which use trade_id="orphan_...") can still be closed properly via broker_position_id.
                target_pos_id = trade.broker_position_id or trade.trade_id
                close_res = adapter.close_position(symbol=trade.symbol, position_id=target_pos_id, side=trade.direction, volume=trade.quantity)

                if close_res.get("status") == "CLOSED":
                    trade.status = "CLOSED"
                    trade.exit_price = current_price

                    # Do NOT use simplistic math. Use authoritative MT5 history if available.
                    actual_pnl = None
                    if adapter.mt5 and settings.TRADING_MODE != "PAPER_TRADING":
                        from datetime import datetime, timezone
                        trade.closed_at = datetime.now(timezone.utc)
                        pos_id = trade.broker_position_id or trade.trade_id
                        if pos_id and pos_id.isdigit():
                            deals = adapter.mt5.history_deals_get(position=int(pos_id))
                            if deals:
                                actual_pnl = sum([d.profit + d.commission + d.swap + d.fee for d in deals])

                    if actual_pnl is not None:
                        trade.pnl = actual_pnl
                        log_event("INFO", "PositionManager", f"Trade {trade.trade_id} closed on broker. Exact PnL: ${actual_pnl:.2f}")
                    else:
                        trade.pnl = pnl # Fallback only for paper trading / mock environments where history is unavailable
                        log_event("INFO", "PositionManager", f"Trade {trade.trade_id} closed on broker. Est PnL: ${pnl:.2f}")

                    db.commit()
                else:
                    log_event("ERROR", "PositionManager", f"Failed to close trade {trade.trade_id} on broker: {close_res}")
    except Exception as e:
        log_event("ERROR", "PositionManager", f"Failed to manage positions: {e}")
    finally:
        db.close()

import threading
from app.monitoring.dashboard.main import trading_state

# Global shutdown event for graceful exit
shutdown_event = threading.Event()

def _supervised_mt5_connect(adapter):
    """Supervised connection loop with exponential backoff up to 60s."""
    backoff = 2
    while not shutdown_event.is_set():
        if adapter.connect():
            log_event("INFO", "MT5Adapter", "Successfully connected to MT5.")
            return True
        log_event("ERROR", "MT5Adapter", f"Connection failed. Retrying in {backoff}s...")
        shutdown_event.wait(backoff)
        backoff = min(60, backoff * 2)
    return False

def run_startup_reconciliation(adapter: MT5Adapter):
    log_event("INFO", "Reconciliation", "Starting Startup Reconciliation...")
    db = SessionLocal()
    try:
        db_trades = db.query(Trade).filter(Trade.status == "OPEN").all()
        db_tickets = {int(t.broker_position_id): t for t in db_trades if t.broker_position_id and t.broker_position_id.isdigit()}

        # We only reconcile against broker if we are not in paper mode
        if settings.TRADING_MODE == "PAPER_TRADING" or not adapter.mt5:
            log_event("INFO", "Reconciliation", "Paper trading mode. Skipping broker query.")
            return

        broker_positions = adapter.mt5.positions_get()
        if broker_positions is None:
            log_event("ERROR", "Reconciliation", "Failed to fetch broker positions. Aborting reconciliation.")
            return

        broker_tickets = {p.ticket: p for p in broker_positions}

        # 1. Detect DB positions missing from Broker (Broker closed them)
        for ticket, trade in db_tickets.items():
            if ticket not in broker_tickets:
                log_event("WARNING", "Reconciliation", f"DB trade {ticket} is closed on broker. Syncing DB...")
                trade.status = "CLOSED"

                # Fetch exact PnL
                deals = adapter.mt5.history_deals_get(position=ticket)
                if deals:
                    trade.pnl = sum([d.profit + d.commission + d.swap + d.fee for d in deals])

        # 2. Detect Broker positions missing from DB (Orphans)
        import uuid
        for ticket, pos in broker_tickets.items():
            if ticket not in db_tickets:
                log_event("WARNING", "Reconciliation", f"ORPHAN BROKER POSITION {ticket} detected! Syncing local DB to track it.")
                # Map MT5 position back to a local Trade object to prevent duplicate entries
                orphan_trade = Trade(
                    trade_id=f"orphan_{ticket}",
                    broker_order_id=str(ticket),
                    broker_position_id=str(ticket),
                    symbol=pos.symbol if hasattr(pos, "symbol") else settings.DEFAULT_SYMBOL,
                    direction="LONG" if getattr(pos, "type", 0) == 0 else "SHORT",
                    quantity=getattr(pos, "volume", 0.0),
                    status="OPEN",
                    entry_price=getattr(pos, "price_open", 0.0)
                )
                db.add(orphan_trade)

        db.commit()
        log_event("INFO", "Reconciliation", "Startup Reconciliation Complete.")
    except Exception as e:
        log_event("ERROR", "Reconciliation", f"Startup reconciliation failed: {e}")
    finally:
        db.close()

def run_trading_loop():
    log_event("INFO", "TradingLoop", f"Background thread spawned for {settings.DEFAULT_SYMBOL}...")

    adapter = MT5Adapter()
    strategy = StrategyEngine()
    ai = AIBrain(settings.AI_MODEL_NAME)
    risk_engine = RiskEngine()

    _supervised_mt5_connect(adapter)
    run_startup_reconciliation(adapter)

    log_event("INFO", "TradingLoop", "Ready. Waiting for START signal from UI.")

    loop_count = 0
    last_candle_time = None

    while not shutdown_event.is_set():
        try:
            shutdown_event.wait(2) # Check interval
            if shutdown_event.is_set():
                break

            # Supervised reconnection if lost
            if not adapter.connected:
                log_event("ERROR", "MT5Adapter", "Lost connection to MT5. Pausing trading.")
                trading_state["active"] = False
                _supervised_mt5_connect(adapter)
                continue

            data = adapter.fetch_ohlcv(settings.DEFAULT_SYMBOL, "1H")
            if not data:
                continue

            current_price = data[-1]['close']
            current_candle_time = data[-1]['time']

            # 1. Manage existing positions with dynamic early exit logic
            # We do this REGARDLESS of trading_state.active so we don't abandon open trades
            # CRITICAL FIX: Pass ONLY closed candles to prevent early exit repainting
            manage_open_positions(current_price, data[:-1], strategy, adapter)

            # If trading is stopped by UI, skip opening new positions
            if not trading_state.get("active", False):
                continue

            # Periodic scan logging to show activity
            loop_count += 1
            if loop_count % 5 == 0:
                log_event("INFO", "TradingLoop", f"Scanning {settings.DEFAULT_SYMBOL} at ${current_price:.2f}...")

            # 2. Look for new setups ONLY on new closed candle to prevent repainting
            if last_candle_time is None or current_candle_time != last_candle_time:
                # Update last candle time immediately to prevent spamming the same candle
                last_candle_time = current_candle_time

                # Pass only closed candles (all except the last one which is still forming)
                candidates = strategy.evaluate_market_data(data[:-1])

                if candidates.get("status") in ["NO_DATA", "WAIT", "NO_TRADE"]:
                    # Suppress spammy wait logs
                    pass
                else:
                    # 2.5 LIVE TRADING GUARD
                    # Ensure we do not execute real trades if the app is explicitly in PAPER_TRADING mode
                    if adapter.mt5:
                        acc_info = adapter.mt5.account_info()
                        if acc_info and acc_info.trade_mode == adapter.mt5.ACCOUNT_TRADE_MODE_REAL and settings.TRADING_MODE != "LIVE_TRADING":
                            log_event("ERROR", "SafetyGuard", "CRITICAL: Live MT5 account detected but TRADING_MODE is not LIVE_TRADING. Aborting execution.")
                            trading_state["active"] = False
                            continue

                    log_event("INFO", "Strategy", f"Signal: {candidates.get('direction')} | {candidates.get('reason')}")

                    direction = candidates.get('direction')

                    # 3. Position Manager Check (Enforce ONE_POSITION_PER_SYMBOL)
                    if has_open_position(settings.DEFAULT_SYMBOL):
                        log_event("INFO", "PositionManager", f"Existing position already open for {settings.DEFAULT_SYMBOL}: NO_TRADE")
                        continue

                    decision = ai.evaluate_candidates(candidates, {})

                    if decision.get("action") == "NO_TRADE":
                        log_event("INFO", "AI", f"Decision: NO_TRADE | Reason: {decision.get('reasoning_summary')}")
                        continue # CRITICAL FIX: Do not proceed to Risk Engine if AI says NO_TRADE

                    log_event("INFO", "AI", f"Decision: {decision.get('action')} | Confidence: {decision.get('confidence'):.2f}")

                    trade_proposal = {
                        "risk_percent": settings.MAX_RISK_PER_TRADE,
                        "leverage": settings.MAX_LEVERAGE,
                        "symbol": settings.DEFAULT_SYMBOL,
                        "side": decision["action"]
                    }

                    account_state = calculate_account_risk_state(adapter)

                    if account_state is None:
                        log_event("ERROR", "RiskEngine", "Risk state unavailable. Failsafe activated: NO TRADE.")
                        continue

                    # ENFORCE RISK ENGINE
                    is_valid, reason = risk_engine.validate_trade(trade_proposal, account_state)
                    if not is_valid:
                        log_event("WARNING", "RiskEngine", f"REJECTED: {reason}")
                        continue

                    sl = candidates.get("stop_loss")
                    tp = candidates.get("take_profit")

                    # Calculate TRUE Risk-Based Position Size
                    contract_size = 100.0
                    volume_step = 0.01
                    volume_min = 0.01
                    volume_max = 100.0

                    if adapter.mt5:
                        symbol_info = adapter.mt5.symbol_info(settings.DEFAULT_SYMBOL)
                        if symbol_info:
                            contract_size = symbol_info.trade_contract_size or contract_size
                            volume_step = symbol_info.volume_step or volume_step
                            volume_min = symbol_info.volume_min or volume_min
                            volume_max = symbol_info.volume_max or volume_max

                    # Position Size = Monetary Risk / (SL Distance * Contract Size)
                    if sl and sl != current_price:
                        sl_distance = abs(current_price - sl)
                        monetary_risk = account_state["equity"] * settings.MAX_RISK_PER_TRADE
                        raw_quantity = monetary_risk / (sl_distance * contract_size)
                    else:
                        # Fallback for strategies without SL
                        raw_quantity = (account_state["equity"] * settings.MAX_LEVERAGE) / (current_price * contract_size)

                    # Normalize Volume to Broker Specs
                    import math
                    quantity = math.floor(raw_quantity / volume_step) * volume_step

                    if quantity < volume_min:
                        log_event("WARNING", "RiskManager", f"Calculated quantity {quantity} is below broker minimum {volume_min}. REJECTING TRADE to protect risk constraints.")
                        continue

                    quantity = min(quantity, volume_max)

                    # Determine decimal precision based on volume_step
                    # e.g. 0.01 -> 2 decimals, 0.1 -> 1 decimal
                    step_str = f"{volume_step:.8f}".rstrip('0').rstrip('.')
                    if '.' in step_str:
                        precision = len(step_str.split('.')[1])
                    else:
                        precision = 0
                    quantity = round(quantity, precision)

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
                    log_event("INFO", "Execution", f"{result.get('status')} - ID: {result.get('order_id', 'N/A')} - MSG: {result.get('error', result.get('comment', 'OK'))}")

                    if result.get("status") in ["SUBMITTED", "FILLED"]:
                        # Handle mock vs live order IDs
                        final_order_id = result.get("order_id", str(uuid.uuid4()))
                        final_position_id = result.get("position_id", final_order_id)
                        final_entry_price = result.get("fill_price", current_price)
                        req_price = order.get("price", current_price)

                        db = SessionLocal()
                        try:
                            trade = Trade(
                                trade_id=final_order_id,
                                broker_order_id=final_order_id,
                                broker_position_id=final_position_id,
                                symbol=settings.DEFAULT_SYMBOL,
                                direction=direction, # Correctly save LONG/SHORT instead of BUY/SELL
                                quantity=quantity,
                                status="OPEN",
                                entry_price=final_entry_price,
                                stop_loss=candidates.get("stop_loss"),
                                take_profit=candidates.get("take_profit"),
                                requested_price=req_price,
                                slippage=abs(final_entry_price - req_price),
                                retcode=result.get("retcode", 0),
                                broker_comment=result.get("comment", result.get("error", ""))
                            )
                            db.add(trade)
                            db.commit()
                        except Exception as e:
                            log_event("ERROR", "Execution", f"Failed to log trade to DB: {e}")
                        finally:
                            db.close()

            # Sleep to prevent spamming the CPU/API
            shutdown_event.wait(5)

        except Exception as e:
            log_event("ERROR", "TradingLoop", f"Exception in trading loop: {e}")
            shutdown_event.wait(10)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous AI Trading System")
    parser.add_argument("--mode", type=str, choices=["dashboard", "backtest", "paper", "live", "replay", "shadow"], default="dashboard")
    args = parser.parse_args()

    if args.mode == "dashboard":
        print("Starting monitoring dashboard & Background Trading Thread...")

        # Start trading thread in background
        t = threading.Thread(target=run_trading_loop, daemon=True)
        t.start()

        try:
            # Start FastAPI
            uvicorn.run(dashboard_app, host="127.0.0.1", port=8000)
        finally:
            print("Shutting down Trading Loop gracefully...")
            shutdown_event.set()
            t.join(timeout=5)
            import MetaTrader5 as mt5
            mt5.shutdown()
    elif args.mode == "backtest":
        run_backtest()
    else:
        print(f"Mode {args.mode} is now managed via the dashboard UI.")
