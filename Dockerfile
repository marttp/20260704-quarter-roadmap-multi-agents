# Multi-stage Dockerfile for Cloud Run (codelab 09 pattern).
# Stage 1 builds the Vue SPA; stage 2 runs FastAPI + the built SPA.

# ---------- Stage 1: build the Vue dashboard ----------
FROM node:22-alpine AS frontend

WORKDIR /repo

# Copy the frontend manifest first for better layer caching.
COPY frontend/package.json frontend/package-lock.json* ./frontend/
RUN cd frontend && npm ci

# Copy the rest of the frontend source + the submission_frontend dir so Vite's
# outDir (../submission_frontend/static/spa) resolves inside the image.
COPY frontend/ ./frontend/
COPY submission_frontend/ ./submission_frontend/

RUN cd frontend && npm run build


# ---------- Stage 2: Python runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Install uv for fast dependency install.
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /app

# Install Python dependencies first (better layer caching).
COPY pyproject.toml uv.lock* ./
RUN uv sync --extra all --no-dev

# Copy the application code + bundled data.
COPY app/ ./app/
COPY data/ ./data/
COPY mcp_server/ ./mcp_server/
COPY submission_frontend/ ./submission_frontend/

# Copy the built Vue SPA from stage 1.
COPY --from=frontend /repo/submission_frontend/static/spa/ ./submission_frontend/static/spa/

EXPOSE 8080

# Cloud Run sets PORT; FastAPI must listen on 0.0.0.0.
CMD ["sh", "-c", "uv run uvicorn submission_frontend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
