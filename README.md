# Train Viewer

Live "train board" for the West Ave and East Ave bridges on the Weaver line, Walthamstow.
There is one countdown per direction, timed at the West Ave bridge.
See [HANDOFF.md](HANDOFF.md) for the design.

## Setup

```bash
conda env create -f environment.yml   # Python 3.12 + Node 22
conda activate train-viewer
cp .env.example .env                  # then add your TFL_APP_KEY
cd frontend && npm install
```

## Run (dev)

Two terminals, both with `conda activate train-viewer`:

```bash
cd backend && uvicorn app.main:app --reload    # http://localhost:8000
cd frontend && npm run dev                     # http://localhost:5173
```

Open http://localhost:5173. Vite proxies `/api` and `/ws` to the backend.

## Track geometry

`backend/data/` (track, stations, chainages) is generated once and committed.
Rebuild it only if the bridges or route change:

```bash
cd backend && python -m scripts.build_geometry
```

It pulls the track from OpenStreetMap (Overpass) and the stations from TfL.

## Test

```bash
cd backend && pytest
```
