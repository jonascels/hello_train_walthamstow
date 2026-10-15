"""Data shapes shared between prediction sources, the ETA service and the API.

All datetimes are timezone-aware UTC.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# British railway convention: "down" = away from London (chainage increasing),
# "up" = towards London (chainage decreasing).
Direction = Literal["up", "down"]


class TimingPoint(BaseModel):
    """A train's predicted (or, later, actual) time at one station."""

    station_id: str  # TfL NaPTAN id, e.g. 910GWLTWCEN
    chainage_m: float
    arr: datetime | None  # predicted/actual arrival
    dep: datetime | None  # predicted/actual departure (TfL doesn't provide this)


class TrainService(BaseModel):
    """One train as reported by a source: its upcoming calls on our route.

    `calls` are in travel order. Stations the train has already passed are not
    included (TfL drops them), so the first call is the next station ahead.
    """

    id: str  # vehicle/service id from the source
    direction: Direction
    destination: str
    calls: list[TimingPoint]
    observed_at: datetime  # when the source produced this prediction


class Train(BaseModel):
    """A train that will pass (or has just passed) the timing bridge.

    `prev`/`next` are the stations either side of the bridge in travel order;
    `prev.dep` and `next.arr` are always set (estimated where necessary).
    """

    id: str
    direction: Direction
    destination: str
    prev: TimingPoint
    next: TimingPoint
    t_bridge: datetime  # estimated time at the bridge


class BridgeSnapshot(BaseModel):
    generated_at: datetime  # server time; the frontend uses it for clock offset
    bridge_id: str
    bridge_chainage_m: float
    trains: list[Train]  # soonest first


class LiveUpdate(BaseModel):
    """What the WebSocket sends after every poll (and on connect)."""

    type: Literal["update"] = "update"
    server_time: datetime  # when this message was sent; for clock offset
    source: str  # data attribution, e.g. "TfL"
    snapshot: BridgeSnapshot | None  # None until the first successful poll
    last_success: datetime | None
    last_error: str | None  # set when the latest poll failed (data is stale)
