from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_config_has_no_secrets() -> None:
    body = client.get("/api/config").json()
    assert "line_id" in body
    assert "tfl_app_key" not in body


def test_ws_heartbeat() -> None:
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "heartbeat"
