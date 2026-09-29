from typing import Dict, Any, List
import pandas as pd
import pandas_ta as ta

class StrategyEngine:
    def __init__(self):
        self.active_strategies = ["Gold Trend & Momentum"]

    def evaluate_market_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyzes market structure and generates potential setups for XAUUSD.
        Uses 50 EMA, 200 EMA, and RSI(14).
        """
        if not data or len(data) < 200:
            return {"status": "NO_DATA", "reason": "Not enough data for EMAs (need 200+ candles)."}

        df = pd.DataFrame(data)

        # Calculate Indicators using pandas-ta
        df.ta.ema(length=9, append=True)
        df.ta.ema(length=21, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.ema(length=200, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.atr(length=14, append=True)

        latest = df.iloc[-1]

        # We need the columns to exist, if they don't, return NO_TRADE
        if 'EMA_50' not in df.columns or 'EMA_200' not in df.columns or 'RSI_14' not in df.columns or 'ATRr_14' not in df.columns or 'EMA_9' not in df.columns or 'EMA_21' not in df.columns:
            return {"status": "NO_TRADE", "reason": "Indicators failed to calculate."}

        ema_50 = latest['EMA_50']
        ema_200 = latest['EMA_200']
        rsi = latest['RSI_14']
        atr = latest['ATRr_14']
        close_price = latest['close']

        # Bullish condition: 50 EMA > 200 EMA (Uptrend) and RSI < 45 (Loosened for more activity)
        if ema_50 > ema_200 and rsi < 45:
            stop_loss = close_price - (atr * 1.5)
            take_profit = close_price + (atr * 3.0) # 1:2 Risk Reward minimum

            return {
                "symbol": "XAUUSD",
                "direction": "LONG",
                "confidence": 0.85,
                "strategy": "Gold Trend & Momentum",
                "entry_price": close_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_reward_ratio": (take_profit - close_price) / (close_price - stop_loss),
                "reason": f"Uptrend (EMA50 > EMA200) with RSI ({rsi:.2f}). ATR: {atr:.2f}"
            }

        # Bearish condition: 50 EMA < 200 EMA (Downtrend) and RSI > 55 (Loosened for more activity)
        elif ema_50 < ema_200 and rsi > 55:
            stop_loss = close_price + (atr * 1.5)
            take_profit = close_price - (atr * 3.0)

            return {
                "symbol": "XAUUSD",
                "direction": "SHORT",
                "confidence": 0.85,
                "strategy": "Gold Trend & Momentum",
                "entry_price": close_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_reward_ratio": (close_price - take_profit) / (stop_loss - close_price),
                "reason": f"Downtrend (EMA50 < EMA200) with RSI ({rsi:.2f}). ATR: {atr:.2f}"
            }

        return {"status": "WAIT", "reason": f"No signal. RSI: {rsi:.2f}, EMA50: {ema_50:.2f}, EMA200: {ema_200:.2f}"}

    def check_early_exit(self, data: List[Dict[str, Any]], direction: str) -> bool:
        """
        Dynamically checks if a trade should be exited early to cut losses.
        Uses 9 EMA and 21 EMA crossovers to detect trend invalidation.
        """
        if not data or len(data) < 21:
            return False

        df = pd.DataFrame(data)
        df.ta.ema(length=9, append=True)
        df.ta.ema(length=21, append=True)

        if 'EMA_9' not in df.columns or 'EMA_21' not in df.columns:
            return False

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        # If we are LONG, and 9 EMA crosses BELOW 21 EMA, trend is dying. Exit early.
        if direction == "LONG":
            if previous['EMA_9'] >= previous['EMA_21'] and latest['EMA_9'] < latest['EMA_21']:
                return True

        # If we are SHORT, and 9 EMA crosses ABOVE 21 EMA, trend is dying. Exit early.
        elif direction == "SHORT":
            if previous['EMA_9'] <= previous['EMA_21'] and latest['EMA_9'] > latest['EMA_21']:
                return True

        return False
