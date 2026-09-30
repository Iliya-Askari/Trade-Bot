import sys
import logging
from typing import Dict, Any, List
from app.core.interfaces import ExecutionProvider, MarketDataProvider
from app.config.settings import settings

logger = logging.getLogger(__name__)

class MT5Adapter(ExecutionProvider, MarketDataProvider):
    def __init__(self):
        self.connected = False

        # MetaTrader5 only works on Windows
        if sys.platform != 'win32':
            logger.warning("MT5Adapter is only supported on Windows. Running in mock mode.")
            self.mt5 = None
            return

        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
        except ImportError:
            logger.warning("MetaTrader5 package is not installed. Running in mock mode.")
            self.mt5 = None

    def connect(self) -> bool:
        if not self.mt5:
            self.connected = True
            return True

        # Pass credentials directly to initialize() if available, to prevent Authorization failed (-6)
        if settings.MT5_LOGIN and settings.MT5_PASSWORD and settings.MT5_SERVER:
            if not self.mt5.initialize(
                login=settings.MT5_LOGIN,
                password=settings.MT5_PASSWORD,
                server=settings.MT5_SERVER
            ):
                logger.error(f"MT5 initialize(with credentials) failed, error code: {self.mt5.last_error()}")
                return False

            authorized = self.mt5.login(
                login=settings.MT5_LOGIN,
                password=settings.MT5_PASSWORD,
                server=settings.MT5_SERVER
            )
            if not authorized:
                logger.error(f"MT5 login failed, error code: {self.mt5.last_error()}")
                return False
        else:
            if not self.mt5.initialize():
                logger.error(f"MT5 initialize() failed, error code: {self.mt5.last_error()}")
                return False
            authorized = True

        # LIVE TRADING SAFETY GUARD
        acc_info = self.mt5.account_info()
        if acc_info:
            if settings.TRADING_MODE != "LIVE_TRADING" and acc_info.trade_mode == self.mt5.ACCOUNT_TRADE_MODE_REAL:
                logger.error("CRITICAL: Connected to a REAL MT5 account, but TRADING_MODE is not LIVE_TRADING. Aborting connection to prevent accidental real money loss.")
                return False

        self.connected = True
        return True

    def fetch_ohlcv(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        if not self.connected:
            return []

        if not self.mt5:
            # Mock data for non-Windows environments (Generate 250 candles to pass EMA200 checks)
            mock_data = []
            import random
            price = 2000.0
            for i in range(250):
                price += random.uniform(-5, 5)
                mock_data.append({
                    "time": f"2024-01-01T{i%24:02d}:00:00Z",
                    "open": price,
                    "high": price + 2,
                    "low": price - 2,
                    "close": price + random.uniform(-1, 1),
                    "volume": 100
                })
            return mock_data

        # Very basic implementation for fetching rates
        # In a real scenario, map `timeframe` to mt5.TIMEFRAME_* constants
        # Request at least 250 candles to satisfy the 200-EMA calculation
        rates = self.mt5.copy_rates_from_pos(symbol, self.mt5.TIMEFRAME_H1, 0, 250)
        if rates is None:
            logger.error(f"Failed to fetch rates for {symbol}")
            return []

        return [
            {
                "time": rate[0],
                "open": rate[1],
                "high": rate[2],
                "low": rate[3],
                "close": rate[4],
                "volume": rate[5]
            } for rate in rates
        ]

    def submit_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        import uuid
        if not self.mt5 or settings.TRADING_MODE == "PAPER_TRADING":
            logger.info(f"PAPER/MOCK MT5 submit_order: {order}")
            return {"status": "SUBMITTED", "order_id": f"mock_mt5_{uuid.uuid4().hex[:8]}"}

        # Simplified order submission logic for MT5
        symbol = order.get("symbol")
        volume = order.get("quantity")
        side = order.get("side", "").upper()
        price = order.get("price")
        sl = order.get("stop_loss")
        tp = order.get("take_profit")

        if side not in ["BUY", "SELL"]:
            logger.error(f"Invalid order side: {side}. Aborting.")
            return {"status": "REJECTED", "error": "Invalid order side"}

        type_dict = {
            "BUY": self.mt5.ORDER_TYPE_BUY,
            "SELL": self.mt5.ORDER_TYPE_SELL
        }

        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": type_dict[side],
            "price": float(price) if price else 0.0,
            "sl": float(sl) if sl else 0.0,
            "tp": float(tp) if tp else 0.0,
            "deviation": 20,
            "magic": 234000,
            "comment": "Autonomous AI Trade",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }

        # For TRADE_ACTION_DEAL (Market Orders), the broker demands the absolute current tick price.
        # Candle close prices will be rejected with INVALID_PRICE.
        tick = self.mt5.symbol_info_tick(symbol)
        if tick:
            request["price"] = tick.ask if side.upper() == "BUY" else tick.bid
        else:
            logger.warning(f"Could not fetch live tick for {symbol}. Order may fail.")

        # Dynamically determine the correct Filling Mode for the Symbol
        symbol_info = self.mt5.symbol_info(symbol)
        if symbol_info:
            filling_mode = symbol_info.filling_mode
            if filling_mode & self.mt5.SYMBOL_FILLING_FOK:
                request["type_filling"] = self.mt5.ORDER_FILLING_FOK
            elif filling_mode & self.mt5.SYMBOL_FILLING_IOC:
                request["type_filling"] = self.mt5.ORDER_FILLING_IOC
            else:
                request["type_filling"] = self.mt5.ORDER_FILLING_RETURN

        # Pre-trade check
        check_result = self.mt5.order_check(request)
        if not check_result or check_result.retcode != self.mt5.TRADE_RETCODE_DONE:
            err = check_result.comment if check_result else "order_check failed entirely"
            ret = check_result.retcode if check_result else 0
            logger.error(f"Order check failed: {ret} - {err}")
            return {"status": "REJECTED", "error": err, "retcode": ret}

        result = self.mt5.order_send(request)
        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order send failed: {result.retcode} - {result.comment}")
            return {"status": "REJECTED", "error": result.comment, "retcode": result.retcode}

        # Get true position ID using history_deals_get, mapping deal -> position
        position_ticket = str(result.order)
        if hasattr(result, 'deal') and result.deal:
            deals = self.mt5.history_deals_get(ticket=result.deal)
            if deals and len(deals) > 0 and hasattr(deals[0], 'position_id'):
                position_ticket = str(deals[0].position_id)
            else:
                position_ticket = str(result.deal)

        return {
            "status": "FILLED",
            "order_id": str(result.order),
            "position_id": position_ticket,
            "fill_price": result.price,
            "retcode": result.retcode,
            "comment": result.comment
        }

    def cancel_order(self, order_id: str) -> bool:
        if not self.mt5:
            logger.info(f"MOCK MT5 cancel_order: {order_id}")
            return True
        return False

    def position_exists(self, position_id: str) -> bool | None:
        """
        Checks if a specific position ticket still exists on the broker.
        Returns:
            True: Position explicitly exists.
            False: Position explicitly does not exist.
            None: Unknown state (e.g. MT5 error or disconnected).
        """
        if not self.mt5 or settings.TRADING_MODE == "PAPER_TRADING":
            # In mock/paper mode, we assume the position exists until we manually close it
            return True

        if not position_id.isdigit():
            return False

        positions = self.mt5.positions_get(ticket=int(position_id))

        # If positions_get returns None, it indicates a failure to fetch data from MT5
        # NOT that the position is absent. We must return None (Unknown) for safety.
        if positions is None:
            last_err = self.mt5.last_error()
            logger.error(f"MT5 positions_get failed for ticket {position_id}. Error: {last_err}")
            return None

        return len(positions) > 0

    def close_position(self, symbol: str, position_id: str, side: str, volume: float) -> Dict[str, Any]:
        """Closes an open position by sending an opposing market order."""
        import uuid
        if not self.mt5 or settings.TRADING_MODE == "PAPER_TRADING":
            logger.info(f"PAPER/MOCK MT5 close_position: {position_id}")
            return {"status": "CLOSED", "order_id": f"mock_close_{uuid.uuid4().hex[:8]}"}

        # Guard against invalid position IDs closing entire symbols
        if not position_id or not position_id.isdigit() or int(position_id) == 0:
            logger.error(f"Cannot close position with invalid ID: {position_id}")
            return {"status": "ERROR", "error": "Invalid position ID"}

        # Get actual tick price for closing
        tick = self.mt5.symbol_info_tick(symbol)
        if not tick:
            return {"status": "ERROR", "error": "Could not get tick data"}

        # Determine opposing order type and price
        close_type = self.mt5.ORDER_TYPE_SELL if side == "LONG" else self.mt5.ORDER_TYPE_BUY
        price = tick.bid if side == "LONG" else tick.ask

        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": close_type,
            "position": int(position_id),
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Autonomous AI Early Exit/SL/TP",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }

        result = self.mt5.order_send(request)
        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            logger.error(f"Position close failed: {result.retcode}")
            return {"status": "ERROR", "error": result.comment}

        # The true position ID might be mapped from the deal rather than just result.order
        return {
            "status": "CLOSED",
            "order_id": str(result.order),
            "position_id": str(result.deal) if hasattr(result, 'deal') and result.deal else str(result.order),
            "fill_price": result.price
        }
