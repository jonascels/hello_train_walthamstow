import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.geometry import load_geometry


def test_stations_in_track_order() -> None:
    geo = load_geometry()
    chainages = [s.chainage_m for s in geo.stations]
    assert chainages == sorted(chainages)
    assert geo.stations[0].id == "910GLIVST"
    assert geo.stations[-1].id == "910GCHINGFD"
    assert chainages[-1] <= geo.track_length_m


def test_timing_bridge_is_between_walthamstow_central_and_wood_street() -> None:
    geo = load_geometry()
    prev, nxt = geo.stations_either_side(geo.timing_bridge.chainage_m)
    assert (prev.id, nxt.id) == ("910GWLTWCEN", "910GWDST")


def test_bridges_are_close_together() -> None:
    by_id = {b.id: b for b in load_geometry().bridges}
    gap = by_id["east-ave"].chainage_m - by_id["west-ave"].chainage_m
    assert 50 < gap < 150


def test_stations_either_side_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        load_geometry().stations_either_side(-10)


def test_track_endpoint() -> None:
    body = TestClient(app).get("/api/track").json()
    assert body["track"]["geometry"]["type"] == "LineString"
    assert len(body["stations"]) == 11
    assert {b["id"] for b in body["bridges"]} == {"west-ave", "east-ave"}
