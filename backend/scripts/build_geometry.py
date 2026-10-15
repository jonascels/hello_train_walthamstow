"""One-off: build the track geometry and chainages for the app.

Run from `backend/`:  python -m scripts.build_geometry

Writes (commit these; the app never queries Overpass at runtime):
  data/track.geojson   the route as a single WGS84 LineString
  data/stations.json   TfL stations on the route (NaPTAN ids, lat/lon)
  data/geometry.json   chainage (metres along the track) of every station and bridge

Chainage is measured from the London end (Liverpool Street) in EPSG:27700
(British National Grid) metres. On British railways "down" is away from London
(chainage increasing) and "up" is towards London (chainage decreasing).
"""

import json
from pathlib import Path

import httpx
from pyproj import Transformer
from shapely import LineString, Point, transform
from shapely.ops import linemerge

from app.config import get_settings

# OSM route relation "Weaver Line: Liverpool Street → Chingford".
# The direction matters: it makes the merged line start at Liverpool Street.
OSM_RELATION_ID = 9683729
# Which of TfL's orderedLineRoutes for the line we follow.
TFL_ROUTE_NAME_CONTAINS = "Chingford"

# Public Overpass servers are often overloaded; try each in turn.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
# Overpass returns 406 to requests without a User-Agent.
USER_AGENT = "train-viewer/0.1 (github.com/jonascels/hello_train_walthamstow)"
# Anything further than this from the track probably means a wrong id or coordinate.
MAX_SNAP_OFFSET_M = 150

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

to_bng = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)


def to_metres(geom):
    """WGS84 (lon, lat) geometry → British National Grid metres."""
    return transform(geom, lambda xy: list(zip(*to_bng.transform(*xy.T))))


def fetch_track() -> LineString:
    """Download the relation's track ways and merge them into one LineString."""
    query = f"[out:json][timeout:60];relation({OSM_RELATION_ID});out body geom;"
    for url in OVERPASS_URLS:
        try:
            resp = httpx.post(
                url,
                data={"data": query},
                headers={"User-Agent": USER_AGENT},
                timeout=90,
            )
            resp.raise_for_status()
            relation = resp.json()["elements"][0]
            break
        except (httpx.HTTPError, ValueError, IndexError) as exc:
            print(f"Overpass {url} failed: {exc!r}")
    else:
        raise RuntimeError("All Overpass servers failed; try again later")

    # Track ways have an empty role; platforms and stops have their own roles.
    ways = [
        LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
        for m in relation["members"]
        if m["type"] == "way" and m["role"] == ""
    ]
    track = linemerge(ways)
    if track.geom_type != "LineString":
        raise RuntimeError(
            f"Track ways did not merge into one line ({track.geom_type}); "
            "the OSM relation may have gaps."
        )
    return track


def fetch_stations(line_id: str) -> list[dict]:
    """Ordered stations (London end first) for the chosen TfL route."""
    resp = httpx.get(
        f"https://api.tfl.gov.uk/Line/{line_id}/Route/Sequence/outbound", timeout=30
    )
    resp.raise_for_status()
    body = resp.json()

    route = next(
        r for r in body["orderedLineRoutes"] if TFL_ROUTE_NAME_CONTAINS in r["name"]
    )
    by_id = {s["id"]: s for seq in body["stopPointSequences"] for s in seq["stopPoint"]}
    return [
        {
            "id": naptan_id,
            "name": by_id[naptan_id]["name"].removesuffix(" Rail Station"),
            "lat": by_id[naptan_id]["lat"],
            "lon": by_id[naptan_id]["lon"],
        }
        for naptan_id in route["naptanIds"]
    ]


def snap(track_m: LineString, lat: float, lon: float, label: str) -> float:
    """Chainage (m) of the point on the track closest to (lat, lon)."""
    point_m = to_metres(Point(lon, lat))
    offset = track_m.distance(point_m)
    if offset > MAX_SNAP_OFFSET_M:
        raise RuntimeError(f"{label} is {offset:.0f} m from the track")
    return round(track_m.project(point_m), 1)


def main() -> None:
    settings = get_settings()
    track = fetch_track()
    track_m = to_metres(track)
    stations = fetch_stations(settings.line_id)

    station_rows = [
        {**s, "chainage_m": snap(track_m, s["lat"], s["lon"], s["name"])}
        for s in stations
    ]
    chainages = [s["chainage_m"] for s in station_rows]
    if chainages != sorted(chainages):
        raise RuntimeError("Stations are not in track order; check the OSM relation")

    bridge_rows = [
        {**b.model_dump(), "chainage_m": snap(track_m, b.lat, b.lon, b.name)}
        for b in settings.bridges
    ]

    DATA_DIR.mkdir(exist_ok=True)
    track_geojson = {
        "type": "Feature",
        "properties": {
            "source": f"OpenStreetMap relation {OSM_RELATION_ID}",
            "attribution": "© OpenStreetMap contributors (ODbL)",
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [[round(x, 7), round(y, 7)] for x, y in track.coords],
        },
    }
    (DATA_DIR / "track.geojson").write_text(json.dumps(track_geojson) + "\n")
    (DATA_DIR / "stations.json").write_text(json.dumps(stations, indent=2) + "\n")
    geometry = {
        "line_id": settings.line_id,
        "track_length_m": round(track_m.length, 1),
        "stations": station_rows,
        "bridges": bridge_rows,
    }
    (DATA_DIR / "geometry.json").write_text(json.dumps(geometry, indent=2) + "\n")

    print(f"Track: {len(track.coords)} points, {track_m.length:.0f} m")
    for row in station_rows + bridge_rows:
        print(f"  {row['chainage_m']:>9.1f} m  {row['name']}")


if __name__ == "__main__":
    main()
