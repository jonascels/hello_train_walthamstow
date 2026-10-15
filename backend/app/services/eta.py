"""Estimate when each train passes the timing bridge.

For each train we find its timing points either side of the bridge (in travel
order) and interpolate linearly by distance:

    t_bridge = t_prev_dep + (t_next_arr - t_prev_dep) * (bridge_m - prev_m) / (next_m - prev_m)

The same formula works in both directions because chainages are signed.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.models import BridgeSnapshot, Direction, TimingPoint, Train, TrainService
from app.services.geometry import Geometry, Station

# TfL gives arrival times only; assume a train leaves this long after arriving.
DWELL = timedelta(seconds=30)
# Used when we never saw the station before the bridge and can't infer speed.
FALLBACK_SPEED_MPS = 13.0  # ≈ 47 km/h, typical between these stations
# Keep showing a train this long after it passed the bridge.
PAST_GRACE = timedelta(seconds=60)
# Forget a vehicle we haven't seen in the feed for this long.
FORGET_AFTER = timedelta(minutes=15)


def _before_bridge(direction: Direction, chainage_m: float, bridge_m: float) -> bool:
    """Is this point reached before the bridge, travelling in `direction`?"""
    return chainage_m <= bridge_m if direction == "down" else chainage_m >= bridge_m


def _speed_from(calls: list[TimingPoint]) -> float:
    """Average speed (m/s) over the first leg of `calls`, or a fallback."""
    if len(calls) >= 2 and calls[0].arr and calls[1].arr:
        seconds = (calls[1].arr - calls[0].arr - DWELL).total_seconds()
        metres = abs(calls[1].chainage_m - calls[0].chainage_m)
        if seconds > 0:
            return metres / seconds
    return FALLBACK_SPEED_MPS


def compute_train(
    service_id: str,
    direction: Direction,
    destination: str,
    calls: list[TimingPoint],
    bridge_m: float,
    stations_either_side: tuple[Station, Station],
) -> Train | None:
    """ETA at the bridge for one train, or None if it doesn't reach the bridge.

    `calls` are in travel order and may include stations already passed.
    `stations_either_side` are the route's stations around the bridge (London
    end first); used only when we never saw the train's previous station.
    """
    before = [c for c in calls if _before_bridge(direction, c.chainage_m, bridge_m)]
    after = [c for c in calls if not _before_bridge(direction, c.chainage_m, bridge_m)]
    if not after or after[0].arr is None:
        return None  # terminates before the bridge, or no usable prediction
    nxt = after[0]

    if before and (before[-1].dep or before[-1].arr):
        prv = before[-1]
        t_dep = prv.dep or prv.arr + DWELL
        # Times are rounded to whole minutes, so the dwell can overshoot.
        if t_dep >= nxt.arr:
            t_dep = min(prv.arr or nxt.arr, nxt.arr)
    else:
        # Never saw the previous station: back-calculate from the next one.
        # Only valid if the next stop is the station just past the bridge;
        # otherwise the train never comes this way (e.g. an up Enfield Town
        # train that joins our route at Hackney Downs).
        london_side, country_side = stations_either_side
        station, expected_next = (
            (london_side, country_side)
            if direction == "down"
            else (country_side, london_side)
        )
        if nxt.station_id != expected_next.id:
            return None
        speed = _speed_from(after)
        t_dep = nxt.arr - timedelta(
            seconds=abs(nxt.chainage_m - station.chainage_m) / speed
        )
        prv = TimingPoint(
            station_id=station.id, chainage_m=station.chainage_m, arr=None, dep=None
        )

    fraction = (bridge_m - prv.chainage_m) / (nxt.chainage_m - prv.chainage_m)
    t_bridge = t_dep + (nxt.arr - t_dep) * fraction
    return Train(
        id=service_id,
        direction=direction,
        destination=destination,
        prev=prv.model_copy(update={"dep": t_dep}),
        next=nxt,
        t_bridge=t_bridge,
    )


@dataclass
class _Seen:
    direction: Direction
    destination: str
    last_seen: datetime
    calls: dict[str, TimingPoint] = field(default_factory=dict)  # by station id


class EtaTracker:
    """Turns successive source fetches into bridge snapshots.

    Remembers each train's calls between polls, because TfL drops a station
    from the feed once the train has passed it, and we still need the time
    at the station before the bridge.
    """

    def __init__(self, geometry: Geometry) -> None:
        self._bridge = geometry.timing_bridge
        self._either_side = geometry.stations_either_side(self._bridge.chainage_m)
        self._seen: dict[str, _Seen] = {}

    def update(self, services: list[TrainService], now: datetime) -> BridgeSnapshot:
        for s in services:
            seen = self._seen.setdefault(s.id, _Seen(s.direction, s.destination, now))
            seen.direction, seen.destination, seen.last_seen = (
                s.direction,
                s.destination,
                now,
            )
            # Newer predictions replace older ones; passed stations are kept.
            seen.calls.update({c.station_id: c for c in s.calls})

        self._seen = {
            vid: seen
            for vid, seen in self._seen.items()
            if now - seen.last_seen <= FORGET_AFTER
        }

        trains = []
        for vid, seen in self._seen.items():
            calls = sorted(
                seen.calls.values(),
                key=lambda c: c.chainage_m,
                reverse=seen.direction == "up",
            )
            train = compute_train(
                vid,
                seen.direction,
                seen.destination,
                calls,
                self._bridge.chainage_m,
                self._either_side,
            )
            if train and train.t_bridge >= now - PAST_GRACE:
                trains.append(train)

        return BridgeSnapshot(
            generated_at=now,
            bridge_id=self._bridge.id,
            bridge_chainage_m=self._bridge.chainage_m,
            trains=sorted(trains, key=lambda t: t.t_bridge),
        )
