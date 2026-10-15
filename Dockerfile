# One container: FastAPI serves the API, the WebSocket and the built frontend.
#   docker build -t train-viewer .
#   docker run -p 8000:8000 -e TFL_APP_KEY=... train-viewer

# --- 1. Build the frontend -------------------------------------------------------
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- 2. Python runtime -----------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/data ./data
# Settings.frontend_dist defaults to <repo>/frontend/dist, i.e. /app/frontend/dist.
COPY --from=frontend /app/frontend/dist /app/frontend/dist

RUN useradd --create-home appuser
USER appuser

# Hosts like Render set $PORT; default 8000 otherwise.
ENV PORT=8000
EXPOSE 8000
# Exactly ONE worker: the TfL poller and the WebSocket subscribers live in
# process memory, so extra workers would poll TfL twice and split clients.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
