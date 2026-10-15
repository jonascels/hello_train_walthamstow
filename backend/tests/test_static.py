from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.static import FrontendFiles


def make_client(tmp_path: Path) -> TestClient:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<h1>board</h1>")
    (tmp_path / "sw.js").write_text("// sw")
    (tmp_path / "assets" / "index-abc123.js").write_text("// app")
    app = FastAPI()
    app.mount("/", FrontendFiles(directory=tmp_path, html=True))
    return TestClient(app)


def test_index_and_service_worker_are_not_cached(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    root = client.get("/")
    assert root.text == "<h1>board</h1>"
    assert root.headers["cache-control"] == "no-cache"
    assert client.get("/sw.js").headers["cache-control"] == "no-cache"


def test_hashed_assets_are_cached_forever(tmp_path: Path) -> None:
    resp = make_client(tmp_path).get("/assets/index-abc123.js")
    assert "immutable" in resp.headers["cache-control"]


def test_api_routes_win_over_frontend() -> None:
    """The real app mounts the frontend last, so /api still works."""
    from app.main import app

    assert TestClient(app).get("/api/health").json()["status"] == "ok"
