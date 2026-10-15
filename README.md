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

To try the production setup locally, run `npm run build` in `frontend/`; the
backend then also serves the built app at http://localhost:8000.

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

## Deploy (Fly.io)

One small always-on machine in London (~$2/month) runs everything: FastAPI
serves the API, the WebSocket and the built frontend from the
[Dockerfile](Dockerfile). Config is in [fly.toml](fly.toml).

First time:

```bash
brew install flyctl
fly auth login
fly apps create hello-train-walthamstow     # or another name; update fly.toml to match
fly secrets set TFL_APP_KEY=your-key        # optional, but raises TfL's rate limit
fly deploy --ha=false
```

`--ha=false` keeps it to **one** machine. Each machine runs its own TfL
poller, so two would double the polling and the cost for no benefit.

After that, `fly deploy` ships new changes. Fly builds the image remotely, so
Docker isn't needed locally. Useful commands: `fly status`, `fly logs`,
`fly open`.

### On the tablet

Open `https://hello-train-walthamstow.fly.dev`, then **Add to Home Screen**
(Safari share menu, or Chrome's install prompt) so it launches full-screen.
HTTPS is what lets the app keep the screen on. As a backstop, also set the
tablet's auto-lock / screen timeout to "never" while it's plugged in.
