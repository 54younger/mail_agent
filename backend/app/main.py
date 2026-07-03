"""FastAPI entry point: ``uvicorn app.main:app``.

Single-user, self-hosted. Binds to localhost (see ``run.py``/README). CORS is
locked to the local frontend origin. When a production frontend build exists it
is served as static files from the same origin (no CORS needed in prod).
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, db
from .api import account, emails, health, jobs, settings, setup, sync, translate

# Local dev frontend origins (Vite).
_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Optional built frontend to serve in production (frontend/dist).
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


_log = logging.getLogger("mail_agent")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Only touch the DB once the user has completed first-run setup. If the
    # recorded data folder is unusable (deleted, unmounted drive, stale path),
    # don't crash startup — forget it and fall back to first-run setup.
    if config.is_configured():
        try:
            await db.init_db()
        except Exception:
            _log.warning(
                "Configured data folder is unusable; resetting to first-run setup.",
                exc_info=True,
            )
            config.clear_data_dir()
            await db.reset_engine()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="mail_agent", version="0.1.0", lifespan=_lifespan)

    origins = os.environ.get("MAIL_AGENT_CORS_ORIGINS", "").split(",")
    origins = [o.strip() for o in origins if o.strip()] or _DEV_ORIGINS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(setup.router)
    app.include_router(account.router)
    app.include_router(sync.router)
    app.include_router(emails.router)
    app.include_router(translate.router)
    app.include_router(settings.router)
    app.include_router(jobs.router)

    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built SPA single-origin: hashed assets from /assets, and an
    index.html fallback for any non-API path so client-side routes (e.g.
    /inbox) survive a refresh/deep-link."""
    if not _FRONTEND_DIST.is_dir():
        return

    assets = _FRONTEND_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    index = _FRONTEND_DIST / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        # API routes are registered earlier and match first; guard anyway so an
        # unknown /api/* path 404s instead of returning the SPA shell.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        return FileResponse(index)


app = create_app()
