"""HTTP endpoints under /api."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request

from app.config import Bridge, get_settings
from app.models import BridgeSnapshot
from app.services.geometry import Geometry, load_geometry

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "server_time": datetime.now(UTC).isoformat()}


@router.get("/config")
async def config() -> dict[str, str | list[Bridge]]:
    """Public, non-secret config the frontend needs (never the API key)."""
    settings = get_settings()
    return {
        "line_id": settings.line_id,
        # From the committed geometry, so production needs no BRIDGES env var
        # (BRIDGES is only read by scripts/build_geometry.py).
        "bridges": [Bridge(**b.model_dump()) for b in load_geometry().bridges],
        "timing_bridge_id": settings.timing_bridge_id,
    }


@router.get("/track")
async def track() -> Geometry:
    """Track line, stations and bridges with chainages, for drawing the map."""
    return load_geometry()


@router.get("/snapshot")
async def snapshot(request: Request) -> BridgeSnapshot:
    """Latest trains and their estimated times at the timing bridge."""
    poller = getattr(request.app.state, "poller", None)
    if poller is None or poller.snapshot is None:
        raise HTTPException(503, "No data yet")
    return poller.snapshot
