from fastapi.testclient import TestClient

from app.main import app
from app.services.geometry import load_geometry
from app.services.poller import Poller
from tests.fakes import FakeSource

# Not used as a context manager, so the app's lifespan (real TfL poller) never runs.
client = TestClient(app)


def test_health() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_config_has_no_secrets() -> None:
    body = client.get("/api/config").json()
    assert "line_id" in body
    assert "tfl_app_key" not in body


def test_snapshot_503_before_first_poll() -> None:
    app.state.poller = Poller(FakeSource([]), load_geometry(), 30)
    assert client.get("/api/snapshot").status_code == 503
