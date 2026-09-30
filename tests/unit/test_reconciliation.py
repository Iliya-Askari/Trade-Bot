import pytest
from app.execution.mt5_adapter import MT5Adapter
from tests.fake_mt5 import FakeMT5
from app.config.settings import settings
import main
from main import run_startup_reconciliation, manage_open_positions

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

def test_startup_reconciliation(adapter, fake_mt5):
    from app.database.session import SessionLocal, engine, Base
    from app.database.models import Trade
    import uuid
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Trade).delete()
    db.commit()

    # 1. Add an active position in DB that is not in MT5 (Broker Closed it)
    trade1_id = "mock_db_only"
    trade1 = Trade(
        trade_id=str(uuid.uuid4()),
        broker_order_id=trade1_id,
        broker_position_id="11111",
        symbol="EURUSD",
        direction="LONG",
        quantity=1.0,
        status="OPEN",
        entry_price=1.1000
    )
    db.add(trade1)

    # 2. Add an active position in MT5 that is not in DB (Orphan Position)
    res = fake_mt5.order_send({
        "action": fake_mt5.TRADE_ACTION_DEAL,
        "volume": 2.0,
        "type": fake_mt5.ORDER_TYPE_SELL,
        "price": 1.1200,
        "sl": 1.1300,
        "tp": 1.1000
    })

    # Commit DB trades
    db.commit()

    # Run reconciliation
    run_startup_reconciliation(adapter)

    # Trade1 should now be closed in DB
    db.refresh(trade1)
    assert trade1.status == "CLOSED"

    # The MT5 orphan should now be mapped in the DB as OPEN
    orphan = db.query(Trade).filter(Trade.broker_position_id == str(res.order)).first()
    assert orphan is not None
    assert orphan.status == "OPEN"
    assert "orphan" in orphan.trade_id

    db.query(Trade).delete()
    db.commit()
    db.close()
