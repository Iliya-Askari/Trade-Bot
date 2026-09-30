import pytest
from app.execution.mt5_adapter import MT5Adapter
from tests.fake_mt5 import FakeMT5
from app.config.settings import settings
import main
from main import calculate_account_risk_state

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

def test_peak_equity_persistence_after_crash(adapter):
    from app.database.session import SessionLocal, engine, Base
    from app.database.models import AccountSnapshot
    from datetime import datetime, timezone, timedelta

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(AccountSnapshot).delete()
    db.commit()

    # 1. Simulate account snapshot populated before a crash
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    snapshot = AccountSnapshot(
        timestamp=past_time,
        day_start_equity=10000.0,
        peak_equity=10500.0 # Reached a peak of 10500
    )
    db.add(snapshot)
    db.commit()

    # 2. Simulate current MT5 equity dropped due to a trade after reboot
    adapter.mt5.account_equity = 10100.0 # Dropped from 10500, but still above start

    # 3. Calculate state (Simulate reboot)
    state = calculate_account_risk_state(adapter)

    # Verify that the system correctly reads the historical peak equity
    # rather than resetting peak equity to 10100.0
    assert state is not None
    assert state["equity"] == 10100.0
    assert state["daily_loss"] == 0.0 # (10100 > 10000, so 0 loss)

    # Drawdown should be calculated from the persisted peak_equity (10500)
    # Drawdown = (10500 - 10100) / 10500 = 400 / 10500 = 0.03809...
    assert abs(state["drawdown"] - 0.038095) < 0.0001

    db.query(AccountSnapshot).delete()
    db.commit()
    db.close()
