from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON
from datetime import datetime
from app.database.session import Base

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(String, unique=True, index=True)
    broker_order_id = Column(String, nullable=True, index=True)
    broker_deal_id = Column(String, nullable=True, index=True)
    broker_position_id = Column(String, nullable=True, index=True)
    symbol = Column(String, index=True)
    direction = Column(String)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    quantity = Column(Float)
    status = Column(String) # OPEN, CLOSED

    # Telemetry
    requested_price = Column(Float, nullable=True)
    slippage = Column(Float, nullable=True)
    retcode = Column(Integer, nullable=True)
    broker_comment = Column(String, nullable=True)
    pnl = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    symbol = Column(String, index=True)
    side = Column(String)
    order_type = Column(String)
    quantity = Column(Float)
    price = Column(Float, nullable=True)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MarketData(Base):
    __tablename__ = "market_data"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True)
    headline = Column(String)
    source = Column(String)
    impact = Column(String) # HIGH, MEDIUM, LOW

class EconomicEvent(Base):
    __tablename__ = "economic_events"
    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String)
    scheduled_time = Column(DateTime, index=True)
    importance = Column(String)
    actual = Column(String, nullable=True)
    consensus = Column(String, nullable=True)
    previous = Column(String, nullable=True)

class SystemEvent(Base):
    __tablename__ = "system_events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String) # INFO, WARNING, ERROR
    module = Column(String)
    message = Column(String)

class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    day_start_equity = Column(Float)
    peak_equity = Column(Float)
