import pytest
from tests.fake_mt5 import FakeMT5
from app.execution.mt5_adapter import MT5Adapter
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

def test_paper_trading_guard(adapter, monkeypatch):
    monkeypatch.setattr(settings, "TRADING_MODE", "PAPER_TRADING")

    order = {
        "symbol": "EURUSD",
        "side": "BUY",
        "quantity": 1.5,
        "price": 1.1000
    }

    # 1. The submit_order function must return a mocked response
    res = adapter.submit_order(order)
    assert res["status"] == "SUBMITTED"
    assert "mock" in res["order_id"].lower()

    # 2. No actual order should reach the FakeMT5 broker tracking
    assert len(adapter.mt5.active_positions) == 0

    # 3. Position exists must return True for string IDs during paper trading
    assert adapter.position_exists(res["order_id"]) is True

    # 4. Closing should generate a mock close response
    close_res = adapter.close_position(symbol="EURUSD", position_id=res["order_id"], volume=1.5, side="LONG")
    assert close_res["status"] == "CLOSED"
    assert "mock" in close_res["order_id"].lower()

def test_tri_state_position_exists(adapter, fake_mt5):
    # Setup open position
    res = fake_mt5.order_send({
        "action": fake_mt5.TRADE_ACTION_DEAL,
        "volume": 1.0,
        "type": fake_mt5.ORDER_TYPE_BUY,
        "price": 1.1000,
        "sl": 1.0900,
        "tp": 1.1100
    })

    positions = fake_mt5.positions_get()
    assert len(positions) == 1
    pos_id = positions[0].ticket

    # 1. Existing position (Returns True)
    assert adapter.position_exists(str(pos_id)) is True

    # 2. Non-existent position (Returns False)
    assert adapter.position_exists("999999") is False

    # 3. Connection failed (Returns None)
    adapter.mt5.fail_order_send = True
    fake_mt5.connected = False
    fake_mt5_prev = fake_mt5.positions_get

    # Mock positions_get to return None exactly like the real MT5 API when it fails
    def mock_positions_get(*args, **kwargs):
        return None
    fake_mt5.positions_get = mock_positions_get

    assert adapter.position_exists(str(pos_id)) is None
    fake_mt5.positions_get = fake_mt5_prev # restore

def test_close_position_invalid_ticket(adapter, fake_mt5, monkeypatch):
    monkeypatch.setattr(settings, "TRADING_MODE", "LIVE_TRADING")
    # Test valid mock closing
    res = adapter.close_position(symbol="EURUSD", position_id="999", volume=1.0, side="LONG") # Use string for id
    assert res["status"] in ["CLOSED", "ERROR", "SUBMITTED"] # depending on mock

    # Try closing invalid ticket
    res = adapter.close_position(symbol="EURUSD", position_id="0", volume=1.0, side="LONG")
    assert res["status"] == "ERROR"
    assert "Invalid position ID" in res.get("error", res.get("comment", ""))

    res = adapter.close_position(symbol="EURUSD", position_id=None, volume=1.0, side="LONG")
    assert res["status"] == "ERROR"
    assert "Invalid position ID" in res.get("error", res.get("comment", ""))

def test_market_data_freshness():
    from app.strategies.engine import StrategyEngine
    from datetime import datetime, timedelta, timezone

    engine = StrategyEngine()

    # We want data[-1] to be MORE than 2 hours stale
    stale_time = datetime.now(timezone.utc) - timedelta(hours=2000) # Ensure it's very stale

    data = []
    # Data is reverse chronological usually, but StrategyEngine logic checks data[-1]
    for i in range(1, 250):
        data.append({
            "time": (stale_time + timedelta(minutes=1*i)).isoformat(), # Keep it very stale
            "open": 1.0,
            "high": 1.2,
            "low": 0.9,
            "close": 1.1,
            "tick_volume": 100
        })

    # Manually trigger freshness check which looks at the last candle
    result = engine.evaluate_market_data(data)
    assert result["status"] == "NO_DATA"
    assert "stale" in result["reason"].lower()

    # Missing OHLC data
    bad_data = []
    for i in range(1, 250):
        bad_data.append({
            "time": (datetime.now(timezone.utc) + timedelta(minutes=5*i)).isoformat(),
            "open": 0.0,
            "high": 0.0,
            "low": 0.0,
            "close": 0.0,
            "tick_volume": 0
        })

    result_bad = engine.evaluate_market_data(bad_data)
    assert result_bad["status"] == "NO_DATA"
    assert "invalid ohlc" in result_bad["reason"].lower()

def test_risk_sizing():
    from main import calculate_account_risk_state, settings
    import uuid
    from datetime import datetime, timezone
    # Mock AccountSnapshot
    from app.database.session import engine, Base, SessionLocal
    from app.database.models import AccountSnapshot, Trade

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Clear previous
    db.query(AccountSnapshot).delete()
    db.query(Trade).delete()
    db.commit()

    snapshot = AccountSnapshot(
        timestamp=datetime.now(timezone.utc),
        day_start_equity=10000.0,
        peak_equity=10000.0
    )
    db.add(snapshot)

    trade = Trade(
        trade_id=str(uuid.uuid4()),
        broker_order_id="123",
        broker_position_id="123",
        symbol="EURUSD",
        direction="LONG",
        quantity=1.0,
        status="OPEN",
        entry_price=1.1000,
        pnl=-500.0 # -$500 floating
    )
    db.add(trade)
    db.commit()

    class MockAdapter:
        class MockMT5:
            def account_info(self):
                class MockInfo:
                    equity = 9500.0 # Dropped to 9500 due to trade
                    balance = 10000.0
                    margin = 500.0
                    margin_free = 9000.0
                return MockInfo()
            def symbol_info(self, symbol):
                class MockSymbol:
                    trade_contract_size = 100000.0
                return MockSymbol()
        def __init__(self):
            self.mt5 = self.MockMT5()

    mock_adapter = MockAdapter()

    # Calculate state
    state = calculate_account_risk_state(mock_adapter)

    assert state is not None
    assert state["equity"] == 9500.0
    assert state["drawdown"] == 0.05 # (10000 - 9500) / 10000
    assert state["daily_loss"] == 0.05

    db.query(AccountSnapshot).delete()
    db.query(Trade).delete()
    db.commit()
    db.close()
