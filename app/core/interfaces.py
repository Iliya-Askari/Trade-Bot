from abc import ABC, abstractmethod
from typing import List, Dict, Any

class MarketDataProvider(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def fetch_ohlcv(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        pass

class ExecutionProvider(ABC):
    @abstractmethod
    def submit_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        pass

class NewsProvider(ABC):
    @abstractmethod
    def fetch_latest(self) -> List[Dict[str, Any]]:
        pass

class EconomicCalendarProvider(ABC):
    @abstractmethod
    def fetch_upcoming_events(self) -> List[Dict[str, Any]]:
        pass
