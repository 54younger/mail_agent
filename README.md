# Mail Agent · 求职邮件助手

A self-hosted email tool focused on a **job-application board (求职看板)**: it syncs your
inbox over IMAP, lets you read and **translate** emails, and uses Claude to extract your
job applications (company / applied-date / status) into a Kanban board.

- **Front/back separated web app** — React frontend + Python (FastAPI) backend.
- **Runs locally, per user** — you run your own backend; on first launch you pick a
  **data folder** that holds your SQLite database. Nothing is uploaded to a central
  server. IMAP password and Claude API key are kept in your OS keyring (never plaintext).
- The previous Flutter/Dart desktop implementation is archived under [`legacy/`](legacy/).

## Architecture

```
frontend/   Vite + React + TypeScript + Tailwind + TanStack Query   (UI)
backend/    FastAPI + SQLAlchemy(async) + SQLite + imap-tools + Claude   (API + sync)
legacy/     archived Flutter desktop app (reference only)
```

The backend binds to `127.0.0.1` only. In dev, Vite proxies `/api` to the backend; in
production the backend serves the built frontend from the same origin.

## Quick start (dev)

Two terminals:

```bash
# 1) backend
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python run.py                                          # http://127.0.0.1:8765

# 2) frontend
cd frontend
pnpm install
pnpm dev                                               # http://localhost:5173
```

Open http://localhost:5173, choose a data folder, then bind your mailbox in 设置.

## Production / distribution (single origin)

Three ways to run it for real, all serving the built UI + API from one origin at
`http://127.0.0.1:8765`:

**One command (no Docker):**

```bash
./start.sh          # builds the frontend, then starts the backend
```

**Manual:**

```bash
cd frontend && pnpm build          # emits frontend/dist
cd ../backend && python run.py     # FastAPI serves the built UI at :8765
```

**Docker (each user gets their own local DB volume):**

```bash
docker compose up --build          # http://127.0.0.1:8765, data in the mailagent-data volume
```

In the Docker image the data folder is the `/data` volume (so first-run folder
selection is skipped) and secrets are kept in an encrypted file inside it (a container
has no OS keyring). For the non-Docker runs you pick a data folder on first launch and
secrets go to your OS keyring.

Sharing with someone else: they clone the repo and run one of the above; each person
keeps their own local database and never touches anyone else's data.

## Status

See [`PLAN.md`](PLAN.md) for the phased roadmap. Phase 0 (restructure + skeletons) is
complete: backend health/config/DB scaffold + ported IMAP error taxonomy (tested), and
a React shell with 求职看板 / 收件箱 / 设置.

## Providers & credentials

163 / QQ / Gmail etc. require an **app-specific auth code** (not your login password) and
IMAP enabled in the mailbox's web settings. The binding wizard surfaces provider-specific
guidance when a connection fails.
