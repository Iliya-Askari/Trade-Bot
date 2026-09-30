import pytest
from app.database.session import SessionLocal, engine, Base
from app.database.models import Trade
import main
import uuid

def test_duplicate_signal_prevention():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Trade).delete()

    # Insert an existing open position
    trade = Trade(
        trade_id=str(uuid.uuid4()),
        broker_order_id="123",
        broker_position_id="123",
        symbol="EURUSD",
        direction="LONG",
        quantity=1.0,
        status="OPEN",
        entry_price=1.1000
    )
    db.add(trade)
    db.commit()

    # The has_open_position function should now return True
    has_pos = main.has_open_position("EURUSD")
    assert has_pos is True

    # And it should return False for symbols without open trades
    assert main.has_open_position("GBPUSD") is False

    db.query(Trade).delete()
    db.commit()
    db.close()
