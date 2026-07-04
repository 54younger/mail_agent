"""Shared fixtures: isolate the data folder + secrets backend per test so nothing
touches the developer's real config or keyring."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point config at an isolated folder via the env override (so set_data_dir's
    bootstrap pointer is never written) and force the file secrets backend."""
    d = tmp_path / "data"
    d.mkdir()
    monkeypatch.setenv("MAIL_AGENT_DATA_DIR", str(d))
    monkeypatch.setenv("MAIL_AGENT_SECRETS_FILE_BACKEND", "1")

    # seed settings.json like real setup does
    (d / "settings.json").write_text('{"translation_target": "en"}', encoding="utf-8")
    return d


@pytest.fixture()
async def app_client(data_dir: Path):
    """A TestClient with a fresh DB initialized in the isolated data folder."""
    from httpx import ASGITransport, AsyncClient

    from app import db
    from app.main import create_app

    await db.reset_engine()
    await db.init_db()

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    await db.reset_engine()
    # reset background-manager module state between tests
    sm = importlib.import_module("app.services.sync_manager")
    sm._state = sm.SyncState()
    em = importlib.import_module("app.services.job_extract_manager")
    em._state = em.ExtractState()
    # Drop the mtime-keyed jobs-config cache so the next test's isolated
    # settings.json is re-read instead of a stale build leaking across tests.
    jc = importlib.import_module("app.services.job_config")
    jc._cache = None
