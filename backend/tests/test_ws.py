"""WebSocket /ws pushes a LiveUpdate on connect and after every poll."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.models import TimingPoint, TrainService
from app.services.geometry import load_geometry
from app.services.poller import Poller
from tests.fakes import FakeSource

GEO = load_geometry()
CH = {s.id: s.chainage_m for s in GEO.stations}


def soon_train() -> TrainService:
    now = datetime.now(UTC)
    return TrainService(
        id="v1",
        direction="down",
        destination="Chingford",
        calls=[
            TimingPoint(
                station_id=sid,
                chainage_m=CH[sid],
                arr=now + timedelta(minutes=m),
                dep=None,
            )
            for sid, m in [("910GWLTWCEN", 1), ("910GWDST", 4)]
        ],
        observed_at=now,
    )


def test_ws_sends_update_on_connect_and_after_each_poll() -> None:
    source = FakeSource([soon_train()])
    poller = Poller(source, GEO, 30)
    app.state.poller = poller
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        first = ws.receive_json()
        assert first["type"] == "update"
        assert first["snapshot"] is None  # nothing polled yet
        assert first["source"] == "Fake"

        ws.portal.call(poller.poll_once)  # run a poll on the app's event loop
        second = ws.receive_json()
        assert second["last_error"] is None
        assert [t["id"] for t in second["snapshot"]["trains"]] == ["v1"]

        source.result = RuntimeError("TfL down")
        ws.portal.call(poller.poll_once)
        third = ws.receive_json()
        assert "TfL down" in third["last_error"]
        # Stale data is still sent, so the screen keeps counting down.
        assert third["snapshot"] == second["snapshot"]

    assert poller._subscribers == set()
