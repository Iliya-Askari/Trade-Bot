import sys
import logging
from typing import Dict, Any, List
from app.core.interfaces import ExecutionProvider, MarketDataProvider
from app.config.settings import settings

logger = logging.getLogger(__name__)

class MT5Adapter(ExecutionProvider, MarketDataProvider):
    def __init__(self):
        self.connected = False
        self.login = settings.MT5_LOGIN
        self.password = settings.MT5_PASSWORD
        self.server = settings.MT5_SERVER

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

        if not self.mt5.initialize():
            logger.error(f"MT5 initialize() failed, error code: {self.mt5.last_error()}")
            return False

        if self.login and self.password and self.server:
            authorized = self.mt5.login(
                login=self.login,
                password=self.password,
                server=self.server
            )
            if not authorized:
                logger.error(f"MT5 login failed, error code: {self.mt5.last_error()}")
                return False

        self.connected = True
        return True

    def fetch_ohlcv(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        if not self.connected:
            return []

        if not self.mt5:
            # Mock data for non-Windows environments
            return [{"time": "2024-01-01T00:00:00Z", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05, "volume": 100}]

        # Very basic implementation for fetching rates
        # In a real scenario, map `timeframe` to mt5.TIMEFRAME_* constants
        rates = self.mt5.copy_rates_from_pos(symbol, self.mt5.TIMEFRAME_H1, 0, 100)
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
        if not self.mt5:
            logger.info(f"MOCK MT5 submit_order: {order}")
            return {"status": "SUBMITTED", "order_id": "mock_mt5_123"}

        # Simplified order submission logic for MT5
        symbol = order.get("symbol")
        volume = order.get("quantity")
        side = order.get("side") # "BUY" or "SELL"

        type_dict = {
            "BUY": self.mt5.ORDER_TYPE_BUY,
            "SELL": self.mt5.ORDER_TYPE_SELL
        }

        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": type_dict.get(side.upper(), self.mt5.ORDER_TYPE_BUY),
            "deviation": 20,
            "magic": 234000,
            "comment": "Autonomous AI Trade",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }

        result = self.mt5.order_send(request)
        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order send failed: {result.retcode}")
            return {"status": "REJECTED", "error": result.comment}

        return {"status": "FILLED", "order_id": str(result.order)}

    def cancel_order(self, order_id: str) -> bool:
        if not self.mt5:
            logger.info(f"MOCK MT5 cancel_order: {order_id}")
            return True

        # Cancellation logic requires full request structure in MT5
        # Simplified here
        return False
