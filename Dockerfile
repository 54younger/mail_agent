# Multi-stage: build the React frontend, then serve it single-origin from FastAPI.

# ── 1) Frontend build ────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
# Install pnpm directly instead of via corepack: node:20's bundled corepack
# ships outdated signing keys and fails to fetch pnpm ("Cannot find matching
# keyid"), which broke `pnpm install`. Pin the same version used locally / in
# package.json's packageManager field so builds are deterministic.
RUN npm install -g pnpm@10.6.3
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# ── 2) Backend runtime ───────────────────────────────────────────────────────
FROM python:3.12-slim AS backend
WORKDIR /app/backend

# Install backend (hatchling needs the package present, so copy first).
COPY backend/ ./
RUN pip install --no-cache-dir .

# Bring in the built frontend so FastAPI serves it at "/" (see app/main.py).
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# Self-hosted single-user defaults. Data + secrets live in the mounted /data
# volume (keyring is unavailable in a container → file-backed secrets).
# MAIL_AGENT_CORS_ORIGINS: the origin(s) allowed to call this local backend.
# When the frontend is hosted on Vercel, set this to your Vercel URL (override
# at `docker run` with `-e MAIL_AGENT_CORS_ORIGINS=https://your-app.vercel.app`).
ENV MAIL_AGENT_HOST=0.0.0.0 \
    MAIL_AGENT_PORT=8765 \
    MAIL_AGENT_DATA_DIR=/data \
    MAIL_AGENT_SECRETS_FILE_BACKEND=1 \
    MAIL_AGENT_CORS_ORIGINS=https://mail-agent-hazel.vercel.app

EXPOSE 8765
CMD ["python", "run.py"]
