"""FastAPI entry point. Run from `backend/`: uvicorn app.main:app --reload"""

from fastapi import FastAPI

from app.api import routes, ws

app = FastAPI(title="Train Viewer")
app.include_router(routes.router)
app.include_router(ws.router)
