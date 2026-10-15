"""TfL Unified API source: /Line/{lineId}/Arrivals.

The endpoint returns one prediction per (train, station) for the next calls of
every train on the line. We group them by `vehicleId` into TrainService objects
and keep only the stations on our route (see data/geometry.json).

Quirks seen in the live data (October 2026):
- Only `expectedArrival` is given, rounded to whole minutes; no departure times.
- A train waiting at its origin terminus is shown "arriving" there in a few
  seconds, regardless of when it actually leaves. Those calls are dropped.
- `direction` is sometimes blank, so we derive it from the destination instead.
- Stations a train has passed disappear from its predictions.
- Works without an app key (rate-limited); responses are cached ~30 s.
"""

from collections import defaultdict
from datetime import datetime
from typing import Any

import httpx

from app.models import Direction, TimingPoint, TrainService
from app.services.geometry import Geometry

TFL_BASE_URL = "https://api.tfl.gov.uk"


def parse_arrivals(raw: list[dict[str, Any]], geometry: Geometry) -> list[TrainService]:
    """Turn TfL Arrivals JSON into TrainServices on our route."""
    chainage = {s.id: s.chainage_m for s in geometry.stations}
    london_end = geometry.stations[0].id
    country_end = geometry.stations[-1].id

    by_vehicle: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in raw:
        if p["naptanId"] in chainage and p.get("vehicleId"):
            by_vehicle[p["vehicleId"]].append(p)

    trains = []
    for vehicle_id, preds in by_vehicle.items():
        destination_id = preds[0]["destinationNaptanId"]
        direction: Direction = "up" if destination_id == london_end else "down"
        # The terminus behind the train is its origin: drop the bogus "arriving
        # now" prediction there (see module docstring).
        origin_id = country_end if direction == "up" else london_end
        preds = [p for p in preds if p["naptanId"] != origin_id]
        if not preds:
            continue

        calls = [
            TimingPoint(
                station_id=p["naptanId"],
                chainage_m=chainage[p["naptanId"]],
                arr=datetime.fromisoformat(p["expectedArrival"]),
                dep=None,
            )
            for p in preds
        ]
        calls.sort(key=lambda c: c.chainage_m, reverse=direction == "up")

        trains.append(
            TrainService(
                id=vehicle_id,
                direction=direction,
                destination=preds[0]["destinationName"].removesuffix(" Rail Station"),
                calls=calls,
                observed_at=max(datetime.fromisoformat(p["timestamp"]) for p in preds),
            )
        )
    return sorted(trains, key=lambda t: t.calls[0].arr or t.observed_at)


class TflSource:
    name = "TfL"

    def __init__(
        self, client: httpx.AsyncClient, line_id: str, app_key: str, geometry: Geometry
    ) -> None:
        self._client = client
        self._line_id = line_id
        self._app_key = app_key
        self._geometry = geometry

    async def fetch(self) -> list[TrainService]:
        params = {"app_key": self._app_key} if self._app_key else {}
        resp = await self._client.get(
            f"{TFL_BASE_URL}/Line/{self._line_id}/Arrivals", params=params, timeout=20
        )
        resp.raise_for_status()
        return parse_arrivals(resp.json(), self._geometry)
