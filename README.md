# Train Viewer

Live "train board" for the West Ave and East Ave bridges on the Weaver line, Walthamstow.
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

## Test

```bash
cd backend && pytest
```
