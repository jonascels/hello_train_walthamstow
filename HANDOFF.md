# Train Viewer — Handoff for Claude Code

## 1. What we're building

A web app (installable PWA) that runs on a tablet as a live "train board" for a fixed spot: a **railway bridge in Walthamstow, London**. It shows:

1. **The line** passing under/over the bridge.
2. **A map** with the track drawn and **small moving icons** marking where approaching and departing trains are *estimated* to be at that moment.
3. **Two countdown timers**, one per direction (e.g. "→ Chingford 2:14", "→ Liverpool St 5:40"), for the next train to pass the bridge.

Owner: Jonas (GitHub `jonascels`). Comfortable with Python, Git, SQL and Streamlit; works in VS Code with conda environments. Newer to frontend JS, so keep the frontend simple, explicit and well commented.

## 2. Key constraint: there is no GPS

Neither TfL nor National Rail (Darwin) publishes train coordinates. They publish **predicted times at stations and timing points**. Train positions must therefore be **interpolated along the track geometry** between the last and next known timing points. Every "position" shown in the app is an estimate. Label it that way in the UI ("estimated position").

## 3. Open decisions (ask Jonas before hard-coding)

- **Which bridge exactly?** Needs a lat/lon. Candidate lines in Walthamstow, both London Overground:
  - **Weaver line**: Liverpool Street ↔ Chingford, via St James Street, Walthamstow Central, Wood Street.
  - **Suffragette line**: Gospel Oak ↔ Barking Riverside, via Blackhorse Road, Walthamstow Queen's Road.
- Store the location in config (`BRIDGE_LAT`, `BRIDGE_LON`, `LINE_ID`), never inline.

## 4. Data sources

| Purpose | Source | Notes |
|---|---|---|
| Live predictions (MVP) | **TfL Unified API** (`api.tfl.gov.uk`) | Free JSON; register for an app key at api-portal.tfl.gov.uk. Use `/Line/{lineId}/Arrivals` and/or `/StopPoint/{id}/Arrivals`. Line IDs are believed to be `weaver` and `suffragette`; **verify via `/Line/Mode/overground`**. |
| Live predictions (later) | **Darwin** via Rail Data Marketplace (raildata.org.uk) | Richer; covers all GB rail. Departure-board API for MVP-style polling; Push Port stream for full network. Free once registered. |
| Track geometry | **OpenStreetMap** via Overpass API | One-off export of `railway=rail` ways for the line → `data/track.geojson`. Commit the file and don't query Overpass at runtime. |
| Station coords | TfL StopPoint API (or NaPTAN) | Store in `data/stations.json`. |

**Secrets:** the API key lives only on the backend (`.env`, git-ignored). The browser never sees it.

## 5. Architecture

```
TfL / Darwin  ──poll 20–30s──▶  FastAPI backend  ──WebSocket──▶  Browser (tablet PWA)
                                 │                               │
                                 ├─ fetch predictions            ├─ MapLibre map + track
                                 ├─ normalise to Train objects   ├─ animate icons every frame
                                 ├─ compute ETA at bridge        │   (Turf.js along())
                                 └─ broadcast snapshot           └─ per-direction countdowns
```

- **Backend owns the truth:** a list of trains with their timing points and the computed ETA at the bridge.
- **Frontend owns the motion:** between snapshots it moves icons smoothly from the timing data and the current clock. No server round-trip per frame.

## 6. Core algorithm

**One-off setup (`scripts/build_geometry.py`)**
1. Load the line's track as a single ordered LineString (merge OSM ways; project to EPSG:27700, British National Grid, for metre distances).
2. Snap the bridge point onto the line, giving `bridge_chainage_m` (distance along the line).
3. Snap each station onto the line, giving `station_chainage_m`.
4. Save to `data/geometry.json`.

**Each poll (`app/services/eta.py`)**
1. For each train, find its **previous** and **next** timing points that bracket the bridge (stations either side of the bridge, in that train's direction).
2. Get the departure time at the previous point (actual if known, else predicted) and the arrival time at the next point.
3. Linear interpolation by distance:
   `t_bridge = t_prev + (t_next - t_prev) * (bridge_m - prev_m) / (next_m - prev_m)`
4. Assign direction (`up`/`down`) from the order of the stations.
5. Drop trains whose `t_bridge` is in the past by more than about 60 s.

**Each animation frame (frontend)**
- `fraction = clamp((now - t_prev) / (t_next - t_prev), 0, 1)`
- `chainage = prev_m + fraction * (next_m - prev_m)`
- Place the icon with `turf.along(track, chainage_km)`.
- A train dwelling in a station sits at the station's chainage.

**Later improvement:** a linear speed model is crude. Optionally model slower speeds near stations (accelerate/decelerate), or use Network Rail Train Describer berth data for finer positions.

## 7. Recommended stack

**Backend (Python 3.12, conda env `train-viewer`)**
- `fastapi`, `uvicorn[standard]`: API + WebSockets
- `httpx`: async HTTP client
- `apscheduler`: polling loop (or a plain `asyncio` task)
- `pydantic` / `pydantic-settings`: models + config from `.env`
- `shapely`, `pyproj`: geometry and chainage
- `pytest`, `respx`: tests with mocked HTTP

**Frontend**
- `vite` + **Svelte** (TypeScript)
- `maplibre-gl`: map; free tiles from **OpenFreeMap** (no key) or a MapTiler free key
- `@turf/along`, `@turf/length`: positions along the track
- `vite-plugin-pwa`: installable on the tablet
- **Screen Wake Lock API**: keep the display on (with a fallback note if unsupported)

## 8. Code outline

```
train-viewer/
├── HANDOFF.md
├── README.md
├── environment.yml              # conda env: python, fastapi, shapely, pyproj, ...
├── .env.example                 # TFL_APP_KEY=, BRIDGE_LAT=, BRIDGE_LON=, LINE_ID=
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, startup: load geometry, start poller
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── models.py            # Train, TimingPoint, BridgeSnapshot
│   │   ├── sources/
│   │   │   ├── base.py          # class PredictionSource(Protocol): async fetch() -> list[Train]
│   │   │   ├── tfl.py           # TfL implementation (MVP)
│   │   │   └── darwin.py        # stub for later
│   │   ├── services/
│   │   │   ├── geometry.py      # load geometry.json; chainage helpers
│   │   │   ├── eta.py           # bracket timing points, interpolate t_bridge
│   │   │   └── poller.py        # periodic fetch → compute → store latest snapshot
│   │   └── api/
│   │       ├── routes.py        # GET /api/config, GET /api/snapshot, GET /api/track
│   │       └── ws.py            # WS /ws: push snapshot on every update
│   ├── scripts/
│   │   └── build_geometry.py    # Overpass → track.geojson → geometry.json
│   ├── data/                    # track.geojson, stations.json, geometry.json (committed)
│   └── tests/
│       ├── test_eta.py          # interpolation edge cases
│       └── fixtures/            # saved TfL responses
└── frontend/
    ├── index.html
    ├── vite.config.ts           # PWA plugin; dev proxy /api and /ws → :8000
    └── src/
        ├── main.ts
        ├── App.svelte           # layout: map (top/left) + countdowns (bottom/right)
        ├── lib/
        │   ├── api.ts           # fetch config/track; WebSocket with auto-reconnect
        │   ├── position.ts      # chainage → [lon, lat] via turf.along
        │   ├── clock.ts         # server-time offset so countdowns don't drift
        │   └── wakeLock.ts
        └── components/
            ├── TrainMap.svelte  # MapLibre, track layer, bridge marker, train icons (rAF loop)
            ├── Countdown.svelte # one per direction: destination, mm:ss, "estimated"
            └── StatusBar.svelte # last update time, connection state, data source credit
```

### Key data shapes

```python
# backend/app/models.py
class TimingPoint(BaseModel):
    station_id: str
    chainage_m: float
    arr: datetime | None      # predicted/actual arrival
    dep: datetime | None      # predicted/actual departure

class Train(BaseModel):
    id: str                   # vehicle/service id from source
    direction: Literal["up", "down"]
    destination: str
    prev: TimingPoint         # bracket either side of the bridge
    next: TimingPoint
    t_bridge: datetime        # computed ETA at bridge

class BridgeSnapshot(BaseModel):
    generated_at: datetime    # server time; frontend uses for clock offset
    bridge_chainage_m: float
    trains: list[Train]
```

```ts
// frontend/src/lib/position.ts
export function chainageAt(train: Train, nowMs: number): number {
  const t0 = Date.parse(train.prev.dep ?? train.prev.arr!);
  const t1 = Date.parse(train.next.arr ?? train.next.dep!);
  const f = Math.min(1, Math.max(0, (nowMs - t0) / (t1 - t0)));
  return train.prev.chainage_m + f * (train.next.chainage_m - train.prev.chainage_m);
}
```

## 9. Milestones

1. **Skeleton:** conda env, FastAPI hello world, Vite+Svelte hello world, dev proxy working.
2. **Geometry:** `build_geometry.py` produces the track and chainages; render track + bridge marker on MapLibre.
3. **Live data:** TfL source fetches arrivals for the line; log normalised `Train` objects.
4. **ETA:** `eta.py` with unit tests (normal case, train dwelling, missing actuals, terminating before the bridge, reversed direction).
5. **Push + countdowns:** WebSocket snapshot → two countdown components.
6. **Animation:** moving icons via `requestAnimationFrame` + `position.ts`.
7. **Tablet polish:** PWA install, wake lock, landscape layout, large type, dark mode, reconnect handling.
8. **Deploy:** single small host (e.g. Fly.io or Render free tier); serve built frontend from FastAPI.
9. **Later:** Darwin source, a location picker (choose any point on any line), a native iOS wrapper for Live Activities.

## 10. Conventions

- Type hints everywhere; `ruff` + `black` for Python, Prettier for TS.
- Times are **UTC in the backend**, converted to Europe/London only for display.
- Never call external APIs from the browser.
- Respect API rate limits; poll no more often than every 20 s.
- Show data attribution in `StatusBar` ("Powered by TfL Open Data" / National Rail as applicable).
- Keep the frontend readable for a Python developer: small components, comments on anything non-obvious.
