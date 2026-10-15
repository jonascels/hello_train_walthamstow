"""FastAPI entry point. Run from `backend/`: uvicorn app.main:app --reload"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api import routes, ws
from app.api.static import FrontendFiles
from app.config import get_settings
from app.services.geometry import load_geometry
from app.services.poller import Poller
from app.sources.tfl import TflSource

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start the poller when the server starts; stop it on shutdown."""
    settings = get_settings()
    geometry = load_geometry()
    async with httpx.AsyncClient() as client:
        source = TflSource(client, settings.line_id, settings.tfl_app_key, geometry)
        poller = Poller(source, geometry, settings.poll_interval_s)
        app.state.poller = poller
        task = asyncio.create_task(poller.run())
        yield
        task.cancel()


app = FastAPI(title="Train Viewer", lifespan=lifespan)
app.include_router(routes.router)
app.include_router(ws.router)

# Production: serve the built frontend from the same origin, so /api and /ws
# need no CORS or proxy. Mounted last so the API routes take priority.
if (dist := get_settings().frontend_dist).is_dir():
    app.mount("/", FrontendFiles(directory=dist, html=True), name="frontend")
