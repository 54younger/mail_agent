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
        "/api/accounts",
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

    # Stub the pipeline as configured. The "Weekly deals" email has no job
    # keyword, so Stage 0 screens it out before classify is ever called; the
    # Acme email passes keyword + classify and extracts to a job.
    monkeypatch.setattr(job_extractor, "classify_configured", lambda: True)
    monkeypatch.setattr(job_extractor, "extract_configured", lambda: True)
    monkeypatch.setattr(job_extractor, "classify_is_job", lambda **k: True)
    monkeypatch.setattr(
        job_extractor, "extract", lambda **k: job_extractor.JobExtraction(True, "Acme", "", 0)
    )

    r = await app_client.post("/api/jobs/extract")
    assert r.status_code == 200
    status = await _wait_extract(app_client)
    assert status["created"] == 1
    assert status["total"] == 2

    jobs = (await app_client.get("/api/jobs")).json()
    assert len(jobs) == 1
    assert jobs[0]["company"] == "Acme"
    assert jobs[0]["source_subject"] == "Application received"

    # Re-extract: both emails are now screened → no candidates, no new job.
    await app_client.post("/api/jobs/extract")
    status = await _wait_extract(app_client)
    assert status["created"] == 0
    assert status["total"] == 0


async def _seed_account_and_emails(app_client, monkeypatch, rows):
    from app.services import imap_sync, sync_manager

    monkeypatch.setattr(imap_sync, "test_connection", lambda *a, **k: None)
    await app_client.post(
        "/api/accounts",
        json={"host": "imap.x.com", "username": "u@x.com", "password": "authcode"},
    )
    monkeypatch.setattr(imap_sync, "fetch_headers", lambda *a, **k: (rows, len(rows), 1))
    monkeypatch.setattr(imap_sync, "fetch_body", lambda *a, **k: "")
    # Extraction's cache phase calls fetch_bodies; default to none (offline).
    monkeypatch.setattr(imap_sync, "fetch_bodies", lambda *a, **k: {})
    await sync_manager.start_sync(full=True)
    await _wait_sync(app_client)


def _stub_pipeline(monkeypatch, company="Acme"):
    from app.services import job_extractor

    monkeypatch.setattr(job_extractor, "classify_configured", lambda: True)
    monkeypatch.setattr(job_extractor, "extract_configured", lambda: True)
    monkeypatch.setattr(job_extractor, "classify_is_job", lambda **k: True)
    monkeypatch.setattr(
        job_extractor, "extract", lambda **k: job_extractor.JobExtraction(True, company, "", 0)
    )


async def test_extract_time_filter(app_client, monkeypatch):
    from app.services import imap_sync

    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new = datetime(2026, 6, 1, tzinfo=timezone.utc)
    rows = [
        imap_sync.EmailRow("1", "INBOX", "hr@acme.com", "me@x.com", "Application received", old),
        imap_sync.EmailRow("2", "INBOX", "hr@beta.com", "me@x.com", "Interview invite", new),
    ]
    await _seed_account_and_emails(app_client, monkeypatch, rows)
    _stub_pipeline(monkeypatch)

    # since excludes the January email → only the June one is a candidate.
    await app_client.post("/api/jobs/extract", params={"since": "2026-05-01T00:00:00+00:00"})
    status = await _wait_extract(app_client)
    assert status["total"] == 1
    assert status["created"] == 1

    jobs = (await app_client.get("/api/jobs")).json()
    assert len(jobs) == 1
    assert jobs[0]["source_subject"] == "Interview invite"


async def test_extract_caches_body_improves_recall(app_client, monkeypatch):
    from app.services import imap_sync

    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    # Subject has NO job keyword; only the body does — subject-only prefilter misses it.
    rows = [imap_sync.EmailRow("77", "INBOX", "hr@acme.com", "me@x.com", "Notification", base)]
    await _seed_account_and_emails(app_client, monkeypatch, rows)
    _stub_pipeline(monkeypatch)
    # The cache phase returns a body containing a job keyword → prefilter now hits.
    monkeypatch.setattr(imap_sync, "fetch_bodies", lambda *a, **k: {"77": "感谢您的申请，诚邀面试"})

    await app_client.post("/api/jobs/extract")
    status = await _wait_extract(app_client)
    assert status["created"] == 1  # would be 0 if the body weren't cached first


async def test_extract_processes_all_across_batches(app_client, monkeypatch):
    from app.services import imap_sync, job_extract_manager

    monkeypatch.setattr(job_extract_manager, "_BATCH_SIZE", 2)
    monkeypatch.setattr(job_extract_manager, "_CONCURRENCY", 2)

    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    rows = [
        imap_sync.EmailRow(str(i), "INBOX", "hr@acme.com", "me@x.com", "Application received", base)
        for i in range(5)
    ]
    await _seed_account_and_emails(app_client, monkeypatch, rows)
    _stub_pipeline(monkeypatch)

    # 5 candidates, batch size 2 → 3 batches; all should be processed.
    await app_client.post("/api/jobs/extract")
    status = await _wait_extract(app_client)
    assert status["total"] == 5
    assert status["current"] == 5
    assert status["created"] == 5

    jobs = (await app_client.get("/api/jobs")).json()
    assert len(jobs) == 5


async def test_summary_dedups_by_company_position(app_client):
    # Same company+position (case/space-insensitive) → one row; the latest event
    # sets current status. A different position at the same company → its own row.
    await app_client.post(
        "/api/jobs",
        json={"company": "Acme", "position": "Backend", "status_code": 0,
              "applied_at": "2026-06-01T00:00:00+00:00"},
    )
    await app_client.post(
        "/api/jobs",
        json={"company": "acme", "position": " backend ", "status_code": 2,
              "applied_at": "2026-06-10T00:00:00+00:00"},
    )
    await app_client.post(
        "/api/jobs",
        json={"company": "Acme", "position": "Frontend", "status_code": 0,
              "applied_at": "2026-06-05T00:00:00+00:00"},
    )

    rows = (await app_client.get("/api/jobs/summary")).json()
    assert len(rows) == 2
    backend = next(r for r in rows if r["position"].strip().lower() == "backend")
    assert backend["count"] == 2
    assert backend["status_code"] == 2  # latest event wins
    assert backend["applied_at"].startswith("2026-06-01")  # earliest
    assert backend["last_update"].startswith("2026-06-10")  # newest


async def test_stats_trend_and_funnel(app_client):
    await app_client.post(
        "/api/jobs",
        json={"company": "A", "position": "X", "status_code": 2,
              "applied_at": "2026-06-01T00:00:00+00:00"},
    )
    await app_client.post(
        "/api/jobs",
        json={"company": "B", "position": "Y", "status_code": 0,
              "applied_at": "2026-06-01T00:00:00+00:00"},
    )
    await app_client.post(
        "/api/jobs",
        json={"company": "C", "position": "Z", "status_code": 3,
              "applied_at": "2026-06-02T00:00:00+00:00"},
    )

    stats = (await app_client.get("/api/jobs/stats")).json()
    assert stats["total"] == 3
    trend = {p["date"]: p["count"] for p in stats["trend"]}
    assert trend == {"2026-06-01": 2, "2026-06-02": 1}
    funnel = {f["status_code"]: f["count"] for f in stats["funnel"]}
    assert funnel[0] == 3  # applied is the base
    assert funnel[2] == 1  # A reached interview
    assert funnel[3] == 1  # C reached offer
    assert abs(stats["interview_rate"] - 1 / 3) < 1e-6
    assert abs(stats["offer_rate"] - 1 / 3) < 1e-6


async def test_extract_captures_position(app_client, monkeypatch):
    from app.services import imap_sync, job_extractor

    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    rows = [imap_sync.EmailRow("9", "INBOX", "hr@acme.com", "me@x.com", "Application received", base)]
    await _seed_account_and_emails(app_client, monkeypatch, rows)
    monkeypatch.setattr(job_extractor, "classify_configured", lambda: True)
    monkeypatch.setattr(job_extractor, "extract_configured", lambda: True)
    monkeypatch.setattr(job_extractor, "classify_is_job", lambda **k: True)
    monkeypatch.setattr(
        job_extractor,
        "extract",
        lambda **k: job_extractor.JobExtraction(True, "Acme", "", 0, position="Backend Engineer"),
    )

    await app_client.post("/api/jobs/extract")
    await _wait_extract(app_client)

    summary = (await app_client.get("/api/jobs/summary")).json()
    assert len(summary) == 1
    assert summary[0]["position"] == "Backend Engineer"


async def _wait_sync(app_client):
    import asyncio

    for _ in range(100):
        s = (await app_client.get("/api/sync/status")).json()
        if not s["running"]:
            return
        await asyncio.sleep(0.02)
    raise AssertionError("sync did not finish")


async def _wait_extract(app_client):
    import asyncio

    for _ in range(200):
        s = (await app_client.get("/api/jobs/extract/status")).json()
        if s["done"] and not s["running"]:
            return s
        await asyncio.sleep(0.02)
    raise AssertionError("extraction did not finish")
