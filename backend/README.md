# mail_agent backend (FastAPI)

Self-hosted, single-user. Talks IMAP, stores everything in a **local SQLite file**
inside a data folder you choose on first run. Secrets (IMAP password, Claude key) go to
the OS keyring, never to disk in plaintext.

## Requirements

- Python 3.11+

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Run

```bash
python run.py                        # http://127.0.0.1:8765
# or pin a data folder (also used by Docker/tests):
MAIL_AGENT_DATA_DIR=./data python run.py
```

The server binds to `127.0.0.1` only. On first run the frontend walks you through
picking a data folder (`POST /api/setup/data-folder`).

## Test

```bash
pytest
```

## Layout

```
app/
├── main.py         # FastAPI app + CORS + optional static frontend
├── config.py       # data-folder resolution + settings.json
├── db.py           # async SQLite engine/session (SQLAlchemy 2.0)
├── core/errors.py  # IMAP error taxonomy (ported from the Flutter app)
├── models/         # SQLAlchemy models (Phase 1)
├── schemas/        # Pydantic DTOs (Phase 1)
├── services/       # imap_sync, translation, job_extractor (Phases 1–3)
└── api/            # routers
```
