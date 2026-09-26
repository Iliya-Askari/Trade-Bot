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

@dashboard_app.get("/api/health")
async def health_check():
    return {"status": "HEALTHY"}
