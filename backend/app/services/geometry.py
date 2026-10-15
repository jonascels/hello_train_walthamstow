"""Load the prebuilt track geometry (see scripts/build_geometry.py)."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import get_settings

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class Station(BaseModel):
    id: str  # TfL NaPTAN id, e.g. 910GWLTWCEN
    name: str
    lat: float
    lon: float
    chainage_m: float


class BridgePoint(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    chainage_m: float


class Geometry(BaseModel):
    """Chainage is metres along the track from the London end (BNG metres)."""

    line_id: str
    track_length_m: float
    stations: list[Station]  # ordered by chainage
    bridges: list[BridgePoint]
    track: dict[str, Any]  # GeoJSON Feature (LineString, WGS84)

    @property
    def timing_bridge(self) -> BridgePoint:
        bridge_id = get_settings().timing_bridge_id
        return next(b for b in self.bridges if b.id == bridge_id)

    def stations_either_side(self, chainage_m: float) -> tuple[Station, Station]:
        """The stations immediately before and after a chainage (London end first)."""
        before = [s for s in self.stations if s.chainage_m <= chainage_m]
        after = [s for s in self.stations if s.chainage_m > chainage_m]
        if not before or not after:
            raise ValueError(f"{chainage_m} m is outside the station range")
        return before[-1], after[0]


@lru_cache
def load_geometry(data_dir: Path = DATA_DIR) -> Geometry:
    raw = json.loads((data_dir / "geometry.json").read_text())
    track = json.loads((data_dir / "track.geojson").read_text())
    return Geometry(**raw, track=track)
