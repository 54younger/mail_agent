"""求职看板 API tests: manual add, status moves (timeline + manually_edited),
and extraction upsert with the manually-edited guard. Claude is stubbed."""

from __future__ import annotations

from datetime import datetime, timezone


async def test_manual_add_and_status_move(app_client):
    r = await app_client.post("/api/jobs", json={"company": "Acme", "status_code": 0})
    assert r.status_code == 200
    job = r.json()
    assert job["company"] == "Acme"
    assert job["manually_edited"] is True
    assert len(job["timeline"]) == 1

    r = await app_client.patch(f"/api/jobs/{job['id']}/status", json={"status_code": 2})
    moved = r.json()
    assert moved["status_code"] == 2
    assert len(moved["timeline"]) == 2
    assert moved["timeline"][-1]["status"] == 2

    jobs = (await app_client.get("/api/jobs")).json()
    assert len(jobs) == 1


async def test_extract_creates_jobs_and_respects_guard(app_client, monkeypatch):
    from app.services import imap_sync, job_extractor, sync_manager

    # Bind an account and seed two emails via a fake sync.
    monkeypatch.setattr(imap_sync, "test_connection", lambda *a, **k: None)
    await app_client.post(
        "/api/account",
        json={"host": "imap.x.com", "username": "u@x.com", "password": "authcode"},
    )
    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    rows = [
        imap_sync.EmailRow("201", "INBOX", "hr@acme.com", "me@x.com", "Application received", base),
        imap_sync.EmailRow("202", "INBOX", "news@promo.com", "me@x.com", "Weekly deals", base),
    ]
    monkeypatch.setattr(imap_sync, "fetch_headers", lambda *a, **k: (rows, 2, 1))
    # Bodies are empty after a header sync; keep extraction offline.
    monkeypatch.setattr(imap_sync, "fetch_body", lambda *a, **k: "")
    await sync_manager.start_sync(full=True)
    await _wait_sync(app_client)

    # Stub the extractor: first email is a job at Acme, second is not.
    def fake_extract(self, *, subject, sender, body):
        if "acme" in sender:
            return job_extractor.JobExtraction(True, "Acme", "", 0)
        return job_extractor.JobExtraction(False, "", "", 99)

    monkeypatch.setattr(job_extractor.JobExtractor, "is_configured", property(lambda self: True))
    monkeypatch.setattr(job_extractor.JobExtractor, "extract", fake_extract)

    r = await app_client.post("/api/jobs/extract")
    assert r.status_code == 200
    assert r.json() == {"created": 1, "scanned": 2}

    jobs = (await app_client.get("/api/jobs")).json()
    assert len(jobs) == 1
    assert jobs[0]["company"] == "Acme"
    assert jobs[0]["source_subject"] == "Application received"

    # Re-extract: the linked email is skipped → no new job.
    r = await app_client.post("/api/jobs/extract")
    assert r.json()["created"] == 0


async def _wait_sync(app_client):
    import asyncio

    for _ in range(100):
        s = (await app_client.get("/api/sync/status")).json()
        if not s["running"]:
            return
        await asyncio.sleep(0.02)
    raise AssertionError("sync did not finish")
