from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os

dashboard_app = FastAPI(title="Trading Dashboard")

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

@dashboard_app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "status": "ONLINE"})

from pydantic import BaseModel
from app.config.settings import settings

class MT5ConfigUpdate(BaseModel):
    login: int
    password: str
    server: str

class SymbolUpdate(BaseModel):
    symbol: str

@dashboard_app.get("/api/health")
async def health_check():
    return {"status": "HEALTHY"}

@dashboard_app.post("/api/config/mt5")
async def update_mt5_config(config: MT5ConfigUpdate):
    settings.MT5_LOGIN = config.login
    settings.MT5_PASSWORD = config.password
    settings.MT5_SERVER = config.server
    return {"status": "success", "message": "MT5 Configuration Updated"}

@dashboard_app.post("/api/config/symbol")
async def update_default_symbol(update: SymbolUpdate):
    settings.DEFAULT_SYMBOL = update.symbol
    return {"status": "success", "message": f"Default symbol updated to {update.symbol}"}

@dashboard_app.get("/api/config")
async def get_config():
    return {
        "MT5_LOGIN": settings.MT5_LOGIN,
        "MT5_SERVER": settings.MT5_SERVER,
        "DEFAULT_SYMBOL": settings.DEFAULT_SYMBOL
    }

from app.database.session import SessionLocal
from app.database.models import SystemEvent, Trade

@dashboard_app.get("/api/logs")
async def get_logs(limit: int = 20):
    db = SessionLocal()
    try:
        events = db.query(SystemEvent).order_by(SystemEvent.timestamp.desc()).limit(limit).all()
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "level": e.level,
                "module": e.module,
                "message": e.message
            } for e in events
        ]
    finally:
        db.close()

@dashboard_app.get("/api/trades")
async def get_trades(limit: int = 10):
    db = SessionLocal()
    try:
        trades = db.query(Trade).order_by(Trade.created_at.desc()).limit(limit).all()
        return [
            {
                "trade_id": t.trade_id,
                "symbol": t.symbol,
                "direction": t.direction,
                "quantity": t.quantity,
                "status": t.status,
                "entry_price": t.entry_price,
                "created_at": t.created_at.isoformat()
            } for t in trades
        ]
    finally:
        db.close()
