"""API-level tests: setup status, account null, empty inbox, sync upsert (no
duplicates), and structured IMAP error responses. imap-tools is stubbed.

Async tests run under pytest-asyncio (asyncio_mode = auto in pyproject)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone


async def test_health_and_empty_state(app_client):
    r = await app_client.get("/api/health")
    assert r.json()["configured"] is True

    assert (await app_client.get("/api/accounts")).json() == []

    page = (await app_client.get("/api/emails")).json()
    assert page == {"items": [], "total": 0, "page": 0, "size": 100, "page_count": 1}


async def test_bind_account_imap_error_is_structured(app_client, monkeypatch):
    from app.core.errors import ImapErrorKind, error_info
    from app.services import imap_sync

    monkeypatch.setattr(
        imap_sync, "test_connection", lambda *a, **k: error_info(ImapErrorKind.AUTH_FAILED)
    )
    r = await app_client.post(
        "/api/accounts",
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
        "/api/accounts",
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


async def test_multiple_accounts_sync_filter_and_delete(app_client, monkeypatch):
    from app.services import imap_sync, sync_manager

    monkeypatch.setattr(imap_sync, "test_connection", lambda *a, **k: None)
    a1 = (
        await app_client.post(
            "/api/accounts",
            json={"host": "imap.163.com", "username": "a@163.com", "password": "p1"},
        )
    ).json()
    a2 = (
        await app_client.post(
            "/api/accounts",
            json={"host": "imap.qq.com", "username": "b@qq.com", "password": "p2"},
        )
    ).json()
    assert a1["id"] != a2["id"]
    assert len((await app_client.get("/api/accounts")).json()) == 2

    base = datetime(2026, 6, 1, tzinfo=timezone.utc)

    def fake_fetch(host, port, use_ssl, username, password, *, full, limit, progress=None):
        # Same UID "1" on both servers → the (account_id, folder, uid) key keeps
        # them distinct instead of colliding.
        if "163" in host:
            rows = [imap_sync.EmailRow("1", "INBOX", "hr@163.com", username, "s163", base)]
        else:
            rows = [
                imap_sync.EmailRow("1", "INBOX", "hr@qq.com", username, "sqq1", base),
                imap_sync.EmailRow("2", "INBOX", "hr@qq.com", username, "sqq2", base),
            ]
        return rows, len(rows), 1

    monkeypatch.setattr(imap_sync, "fetch_headers", fake_fetch)
    await sync_manager.start_sync(full=True)
    await _wait_done(app_client)

    assert (await app_client.get("/api/emails")).json()["total"] == 3
    p1 = (await app_client.get(f"/api/emails?account_id={a1['id']}")).json()
    p2 = (await app_client.get(f"/api/emails?account_id={a2['id']}")).json()
    assert p1["total"] == 1
    assert p2["total"] == 2
    assert all(i["account_id"] == a2["id"] for i in p2["items"])

    # Deleting one account removes only its emails.
    assert (await app_client.delete(f"/api/accounts/{a1['id']}")).status_code == 204
    assert len((await app_client.get("/api/accounts")).json()) == 1
    assert (await app_client.get("/api/emails")).json()["total"] == 2


async def _wait_done(app_client):
    for _ in range(100):
        s = (await app_client.get("/api/sync/status")).json()
        if not s["running"]:
            return s
        await asyncio.sleep(0.02)
    raise AssertionError("sync did not finish")
