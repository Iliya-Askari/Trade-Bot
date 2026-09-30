import pytest
from app.execution.mt5_adapter import MT5Adapter
from tests.fake_mt5 import FakeMT5
from app.config.settings import settings

@pytest.fixture
def fake_mt5():
    return FakeMT5()

@pytest.fixture
def adapter(fake_mt5, monkeypatch):
    adapter = MT5Adapter()
    adapter.mt5 = fake_mt5
    adapter.connected = True
    monkeypatch.setattr(settings, "TRADING_MODE", "LIVE_TRADING")
    return adapter

def test_submit_valid_order(adapter, fake_mt5):
    order = {
        "symbol": "EURUSD",
        "side": "BUY",
        "quantity": 1.5,
        "price": 1.1000,
        "stop_loss": 1.0900,
        "take_profit": 1.1200
    }
    res = adapter.submit_order(order)
    assert res["status"] in ["SUBMITTED", "FILLED"]
    assert res["order_id"] is not None
    assert len(fake_mt5.active_positions) == 1

def test_submit_invalid_side(adapter):
    order = {
        "symbol": "EURUSD",
        "side": "INVALID",
        "quantity": 1.0,
        "price": 1.1000
    }
    res = adapter.submit_order(order)
    assert res["status"] == "REJECTED"
    assert "Invalid order side" in res["error"]

def test_order_rejection_from_broker(adapter, fake_mt5):
    fake_mt5.order_retcode = fake_mt5.TRADE_RETCODE_REJECT
    order = {
        "symbol": "EURUSD",
        "side": "SELL",
        "quantity": 1.0,
        "price": 1.1000
    }
    res = adapter.submit_order(order)
    assert res["status"] == "REJECTED"
    assert "Check OK" in res["error"] or "Forced Failure" in res["error"]
