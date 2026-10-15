"""HTTP endpoints under /api."""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.config import Bridge, get_settings

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "server_time": datetime.now(UTC).isoformat()}


@router.get("/config")
async def config() -> dict[str, str | list[Bridge]]:
    """Public, non-secret config the frontend needs (never the API key)."""
    settings = get_settings()
    return {"line_id": settings.line_id, "bridges": settings.bridges}
