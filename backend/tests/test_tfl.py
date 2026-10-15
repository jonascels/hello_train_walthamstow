"""TfL source tests, using a real /Line/weaver/Arrivals response captured
2026-10-15 ~18:47 UTC (trimmed to the fields we use)."""

import json
from pathlib import Path

import httpx
import pytest
import respx

from app.services.geometry import load_geometry
from app.services.poller import Poller
from app.sources.tfl import TFL_BASE_URL, TflSource, parse_arrivals

FIXTURE = Path(__file__).parent / "fixtures" / "tfl_weaver_arrivals.json"
ARRIVALS_URL = f"{TFL_BASE_URL}/Line/weaver/Arrivals"


@pytest.fixture
def raw() -> list[dict]:
    return json.loads(FIXTURE.read_text())


@pytest.fixture
def trains(raw):
    return parse_arrivals(raw, load_geometry())


def test_only_route_stations_and_one_call_per_station(trains) -> None:
    route = {s.id for s in load_geometry().stations}
    for t in trains:
        ids = [c.station_id for c in t.calls]
        assert set(ids) <= route
        assert len(ids) == len(set(ids))


def test_calls_are_in_travel_order(trains) -> None:
    for t in trains:
        chainages = [c.chainage_m for c in t.calls]
        assert chainages == sorted(chainages, reverse=t.direction == "up")
        times = [c.arr for c in t.calls]
        assert times == sorted(times), t.id


def test_direction_from_destination(trains) -> None:
    for t in trains:
        assert t.direction == (
            "up" if t.destination == "London Liverpool Street" else "down"
        )
    assert {"up", "down"} == {t.direction for t in trains}


def test_origin_terminus_calls_dropped(trains) -> None:
    for t in trains:
        origin = "910GCHINGFD" if t.direction == "up" else "910GLIVST"
        assert origin not in {c.station_id for c in t.calls}


def test_known_train(trains) -> None:
    """The 18:46 Liverpool Street → Chingford, at Walthamstow Central at 19:01."""
    t = next(t for t in trains if t.id == "202610157161730")
    assert (t.direction, t.destination) == ("down", "Chingford")
    by_station = {c.station_id: c.arr for c in t.calls}
    assert by_station["910GWLTWCEN"].strftime("%H:%M") == "19:01"
    assert by_station["910GWDST"].strftime("%H:%M") == "19:04"
    assert by_station["910GWDST"].tzinfo is not None


def test_enfield_trains_kept_on_shared_section(trains) -> None:
    enfield = [t for t in trains if t.destination == "Enfield Town"]
    assert enfield
    for t in enfield:
        assert {c.station_id for c in t.calls} <= {
            "910GBTHNLGR",
            "910GCAMHTH",
            "910GLONFLDS",
            "910GHAKNYNM",
        }


@respx.mock
async def test_fetch_sends_app_key(raw) -> None:
    route = respx.get(ARRIVALS_URL).mock(return_value=httpx.Response(200, json=raw))
    async with httpx.AsyncClient() as client:
        trains = await TflSource(client, "weaver", "secret", load_geometry()).fetch()
    assert trains
    assert route.calls.last.request.url.params["app_key"] == "secret"


@respx.mock
async def test_poller_survives_errors() -> None:
    respx.get(ARRIVALS_URL).mock(return_value=httpx.Response(503))
    async with httpx.AsyncClient() as client:
        geometry = load_geometry()
        poller = Poller(TflSource(client, "weaver", "", geometry), geometry, 30)
        await poller.poll_once()
    assert poller.snapshot is None
    assert poller.last_success is None
    assert "503" in (poller.last_error or "")
