"""ETA at the West Ave bridge.

Real chainages (data/geometry.json): Walthamstow Central 10043.7 m,
West Ave bridge 10321.3 m, Wood Street 11335.8 m, Highams Park 13851.6 m.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.models import TimingPoint, TrainService
from app.services.eta import DWELL, FALLBACK_SPEED_MPS, EtaTracker, compute_train
from app.services.geometry import load_geometry
from app.sources.tfl import parse_arrivals

GEO = load_geometry()
CH = {s.id: s.chainage_m for s in GEO.stations}
BRIDGE_M = GEO.timing_bridge.chainage_m
EITHER_SIDE = GEO.stations_either_side(BRIDGE_M)
# Fraction of the Walthamstow Central → Wood Street gap at which the bridge sits.
F_DOWN = (BRIDGE_M - CH["910GWLTWCEN"]) / (CH["910GWDST"] - CH["910GWLTWCEN"])


def t(hhmmss: str) -> datetime:
    h, m, s = (int(x) for x in hhmmss.split(":"))
    return datetime(2026, 10, 15, h, m, s, tzinfo=UTC)


def call(station: str, arr: str | None, dep: str | None = None) -> TimingPoint:
    return TimingPoint(
        station_id=station,
        chainage_m=CH[station],
        arr=t(arr) if arr else None,
        dep=t(dep) if dep else None,
    )


def eta(direction, calls):
    return compute_train("x", direction, "dest", calls, BRIDGE_M, EITHER_SIDE)


def test_normal_down_train() -> None:
    train = eta("down", [call("910GWLTWCEN", "19:01:00"), call("910GWDST", "19:04:00")])
    t_dep = t("19:01:00") + DWELL
    expected = t_dep + (t("19:04:00") - t_dep) * F_DOWN
    assert train.t_bridge == expected
    assert (train.prev.station_id, train.next.station_id) == ("910GWLTWCEN", "910GWDST")
    assert train.prev.dep == t_dep


def test_reversed_direction_up_train() -> None:
    """Up trains reach Wood Street first; the bridge is near the far end."""
    train = eta("up", [call("910GWDST", "19:00:00"), call("910GWLTWCEN", "19:02:00")])
    t_dep = t("19:00:00") + DWELL
    expected = t_dep + (t("19:02:00") - t_dep) * (1 - F_DOWN)
    assert train.t_bridge == pytest.approx(expected, abs=timedelta(microseconds=10))
    assert (train.prev.station_id, train.next.station_id) == ("910GWDST", "910GWLTWCEN")


def test_known_departure_is_used_over_dwell() -> None:
    """A train dwelling longer than usual: an explicit departure time wins."""
    train = eta(
        "down",
        [call("910GWLTWCEN", "19:01:00", dep="19:02:00"), call("910GWDST", "19:04:00")],
    )
    assert train.prev.dep == t("19:02:00")
    assert train.t_bridge == t("19:02:00") + (t("19:04:00") - t("19:02:00")) * F_DOWN


def test_arrival_times_in_same_minute_do_not_go_backwards() -> None:
    """Minute rounding can make arr + dwell later than the next arrival."""
    train = eta("down", [call("910GWLTWCEN", "19:01:00"), call("910GWDST", "19:01:00")])
    assert train.t_bridge == t("19:01:00")


def test_missing_previous_station_uses_speed_of_next_leg() -> None:
    """First seen after leaving Walthamstow Central (e.g. app just started)."""
    calls = [call("910GWDST", "19:04:00"), call("910GHGHMSPK", "19:07:00")]
    train = eta("down", calls)
    leg_s = 180 - DWELL.total_seconds()
    speed = (CH["910GHGHMSPK"] - CH["910GWDST"]) / leg_s
    expected = t("19:04:00") - timedelta(seconds=(CH["910GWDST"] - BRIDGE_M) / speed)
    assert train.t_bridge == pytest.approx(expected, abs=timedelta(milliseconds=1))
    assert train.prev.station_id == "910GWLTWCEN"
    assert train.prev.arr is None


def test_missing_previous_station_and_no_next_leg_uses_fallback_speed() -> None:
    train = eta("down", [call("910GWDST", "19:04:00")])
    expected = t("19:04:00") - timedelta(
        seconds=(CH["910GWDST"] - BRIDGE_M) / FALLBACK_SPEED_MPS
    )
    assert train.t_bridge == pytest.approx(expected, abs=timedelta(milliseconds=1))


def test_terminating_before_bridge_is_ignored() -> None:
    """E.g. a down train ending at Walthamstow Central, or an Enfield train."""
    assert (
        eta("down", [call("910GSTJMSST", "19:00:00"), call("910GWLTWCEN", "19:02:00")])
        is None
    )
    assert eta("down", [call("910GHAKNYNM", "19:00:00")]) is None


def test_train_joining_route_beyond_bridge_is_ignored() -> None:
    """Up Enfield Town / Cheshunt trains join our route at Hackney Downs, past
    the bridge, so they never cross it (seen in live data)."""
    assert (
        eta("up", [call("910GHAKNYNM", "19:12:00"), call("910GBTHNLGR", "19:16:00")])
        is None
    )


def test_up_train_past_wood_street_only_has_walthamstow_central() -> None:
    """Up train has left Wood Street: TfL now only lists Walthamstow Central onwards."""
    train = eta(
        "up", [call("910GWLTWCEN", "19:02:00"), call("910GSTJMSST", "19:04:00")]
    )
    assert train is not None
    assert train.prev.station_id == "910GWDST"
    assert train.t_bridge < t("19:02:00")


# --- EtaTracker: memory across polls -------------------------------------------------


def service(vid: str, direction, calls, at: str) -> TrainService:
    return TrainService(
        id=vid,
        direction=direction,
        destination="Chingford",
        calls=calls,
        observed_at=t(at),
    )


def test_tracker_remembers_passed_station() -> None:
    tracker = EtaTracker(GEO)
    both = [call("910GWLTWCEN", "19:01:00"), call("910GWDST", "19:04:00")]
    first = tracker.update([service("v1", "down", both, "19:00:00")], t("19:00:00"))

    # Train has left Walthamstow Central, which drops out of the feed.
    later = [call("910GWDST", "19:04:00")]
    second = tracker.update([service("v1", "down", later, "19:02:00")], t("19:02:00"))

    assert second.trains[0].prev.station_id == "910GWLTWCEN"
    assert second.trains[0].t_bridge == first.trains[0].t_bridge


def test_tracker_updates_delayed_prediction() -> None:
    tracker = EtaTracker(GEO)
    tracker.update(
        [
            service(
                "v1",
                "down",
                [call("910GWLTWCEN", "19:01:00"), call("910GWDST", "19:04:00")],
                "19:00:00",
            )
        ],
        t("19:00:00"),
    )
    snap = tracker.update(
        [
            service(
                "v1",
                "down",
                [call("910GWLTWCEN", "19:03:00"), call("910GWDST", "19:06:00")],
                "19:01:00",
            )
        ],
        t("19:01:00"),
    )
    assert snap.trains[0].prev.arr == t("19:03:00")


def test_tracker_drops_trains_after_grace_and_forgets_vehicles() -> None:
    tracker = EtaTracker(GEO)
    calls = [call("910GWLTWCEN", "19:01:00"), call("910GWDST", "19:04:00")]
    snap = tracker.update([service("v1", "down", calls, "19:00:00")], t("19:00:00"))
    t_bridge = snap.trains[0].t_bridge

    assert tracker.update([], t_bridge + timedelta(seconds=59)).trains
    assert not tracker.update([], t_bridge + timedelta(seconds=61)).trains
    tracker.update([], t("19:20:00"))
    assert tracker._seen == {}


def test_snapshot_from_real_tfl_data() -> None:
    raw = json.loads(
        (Path(__file__).parent / "fixtures" / "tfl_weaver_arrivals.json").read_text()
    )
    now = datetime.fromisoformat(raw[0]["timestamp"])
    snap = EtaTracker(GEO).update(parse_arrivals(raw, GEO), now)

    assert snap.bridge_id == "west-ave"
    assert {tr.direction for tr in snap.trains} == {"up", "down"}
    assert all(
        tr.destination in {"Chingford", "London Liverpool Street"} for tr in snap.trains
    )
    times = [tr.t_bridge for tr in snap.trains]
    assert times == sorted(times)
    for tr in snap.trains:
        assert tr.t_bridge >= now - timedelta(seconds=60)
        assert tr.prev.dep <= tr.t_bridge <= tr.next.arr
