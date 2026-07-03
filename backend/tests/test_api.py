"""API-level tests: setup status, account null, empty inbox, sync upsert (no
duplicates), and structured IMAP error responses. imap-tools is stubbed.

Async tests run under pytest-asyncio (asyncio_mode = auto in pyproject)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone


async def test_health_and_empty_state(app_client):
    r = await app_client.get("/api/health")
    assert r.json()["configured"] is True

    assert (await app_client.get("/api/account")).json() is None

    page = (await app_client.get("/api/emails")).json()
    assert page == {"items": [], "total": 0, "page": 0, "size": 100, "page_count": 1}


async def test_bind_account_imap_error_is_structured(app_client, monkeypatch):
    from app.core.errors import ImapErrorKind, error_info
    from app.services import imap_sync

    monkeypatch.setattr(
        imap_sync, "test_connection", lambda *a, **k: error_info(ImapErrorKind.AUTH_FAILED)
    )
    r = await app_client.post(
        "/api/account",
        json={"host": "imap.x.com", "username": "u@x.com", "password": "wrong"},
    )
    assert r.status_code == 400
    body = r.json()
    assert body["kind"] == "auth_failed"
    assert "授权码" in body["hint"]


async def test_bind_then_sync_upserts_without_duplicates(app_client, monkeypatch):
    from app.services import imap_sync, sync_manager

    # Bind succeeds (no IMAP error); password store uses the file backend (no-op keyring).
    monkeypatch.setattr(imap_sync, "test_connection", lambda *a, **k: None)
    r = await app_client.post(
        "/api/account",
        json={"host": "imap.x.com", "username": "u@x.com", "password": "authcode"},
    )
    assert r.status_code == 200

    base = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)

    def fake_rows(n):
        return [
            imap_sync.EmailRow(
                uid=str(100 + i),
                folder="INBOX",
                from_address="hr@corp.com",
                to_addresses="me@x.com",
                subject=f"Offer {i}",
                date=base,
            )
            for i in range(n)
        ]

    # First sync: 3 messages.
    monkeypatch.setattr(imap_sync, "fetch_headers", lambda *a, **k: (fake_rows(3), 3, 7))
    await sync_manager.start_sync(full=True)
    await _wait_done(app_client)

    page = (await app_client.get("/api/emails")).json()
    assert page["total"] == 3

    # Second sync: same 3 UIDs + 1 new → total 4, not 7.
    monkeypatch.setattr(imap_sync, "fetch_headers", lambda *a, **k: (fake_rows(4), 4, 7))
    await sync_manager.start_sync(full=True)
    await _wait_done(app_client)

    page = (await app_client.get("/api/emails")).json()
    assert page["total"] == 4
    assert page["items"][0]["subject"].startswith("Offer")


async def _wait_done(app_client):
    for _ in range(100):
        s = (await app_client.get("/api/sync/status")).json()
        if not s["running"]:
            return s
        await asyncio.sleep(0.02)
    raise AssertionError("sync did not finish")
