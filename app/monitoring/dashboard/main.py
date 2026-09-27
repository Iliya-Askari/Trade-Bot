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
