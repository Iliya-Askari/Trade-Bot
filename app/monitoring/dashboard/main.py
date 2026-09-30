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

class AllocationUpdate(BaseModel):
    allocation: float
    leverage: float

# Global dict to control the background thread safely
trading_state = {"active": False}

@dashboard_app.get("/api/health")
async def health_check():
    return {"status": "HEALTHY"}

# Security/CSRF Protection for dangerous endpoints
from fastapi import Request, HTTPException

def verify_csrf_header(request: Request):
    # Enforce application/json to trigger CORS preflight on browsers, preventing simple CSRF form posts
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type.lower():
        raise HTTPException(status_code=403, detail="Invalid Content-Type for state modifying request. CSRF blocked.")

@dashboard_app.post("/api/trading/start")
async def start_trading(request: Request):
    verify_csrf_header(request)
    trading_state["active"] = True
    from app.database.session import SessionLocal
    from app.database.models import SystemEvent
    db = SessionLocal()
    try:
        db.add(SystemEvent(level="INFO", module="UI", message="OPERATOR ACTIVATED TRADING"))
        db.commit()
    except: pass
    finally: db.close()
    return {"status": "success", "message": "Trading loop activated."}

@dashboard_app.post("/api/trading/stop")
async def stop_trading(request: Request):
    verify_csrf_header(request)
    trading_state["active"] = False
    from app.database.session import SessionLocal
    from app.database.models import SystemEvent
    db = SessionLocal()
    try:
        db.add(SystemEvent(level="INFO", module="UI", message="OPERATOR STOPPED TRADING"))
        db.commit()
    except: pass
    finally: db.close()
    return {"status": "success", "message": "Trading loop stopped."}

@dashboard_app.get("/api/trading/status")
async def get_trading_status():
    return {"active": trading_state["active"]}

@dashboard_app.post("/api/config/mt5")
async def update_mt5_config(config: MT5ConfigUpdate, request: Request):
    verify_csrf_header(request)
    settings.MT5_LOGIN = config.login
    settings.MT5_PASSWORD = config.password
    settings.MT5_SERVER = config.server
    return {"status": "success", "message": "MT5 Configuration Updated"}

@dashboard_app.post("/api/config/symbol")
async def update_default_symbol(update: SymbolUpdate):
    settings.DEFAULT_SYMBOL = update.symbol
    return {"status": "success", "message": f"Default symbol updated to {update.symbol}"}

@dashboard_app.post("/api/config/allocation")
async def update_allocation(update: AllocationUpdate):
    settings.TRADE_ALLOCATION = update.allocation
    settings.MAX_LEVERAGE = update.leverage
    return {"status": "success", "message": f"Allocation updated to ${update.allocation} at {update.leverage}x leverage"}

@dashboard_app.get("/api/config")
async def get_config():
    return {
        "MT5_LOGIN": settings.MT5_LOGIN,
        "MT5_SERVER": settings.MT5_SERVER,
        "DEFAULT_SYMBOL": settings.DEFAULT_SYMBOL,
        "TRADE_ALLOCATION": settings.TRADE_ALLOCATION,
        "MAX_LEVERAGE": settings.MAX_LEVERAGE
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
                "stop_loss": t.stop_loss,
                "take_profit": t.take_profit,
                "pnl": t.pnl,
                "created_at": t.created_at.isoformat()
            } for t in trades
        ]
    finally:
        db.close()

@dashboard_app.get("/api/portfolio")
async def get_portfolio():
    db = SessionLocal()
    try:
        trades = db.query(Trade).all()
        total_pnl = sum([t.pnl for t in trades if t.pnl is not None])
        wins = len([t for t in trades if t.pnl is not None and t.pnl > 0])
        losses = len([t for t in trades if t.pnl is not None and t.pnl <= 0])
        total_closed = wins + losses
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0

        open_trades = [t for t in trades if t.status == "OPEN"]
        active_investment = sum([t.entry_price * t.quantity for t in open_trades])

        return {
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate, 2),
            "total_trades": total_closed,
            "open_positions_count": len(open_trades),
            "active_investment": round(active_investment, 2)
        }
    finally:
        db.close()
