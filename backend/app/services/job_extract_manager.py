"""Background job-extraction orchestration + in-memory progress.

Mirrors ``sync_manager``: the pipeline runs in a background task against its own
DB session so ``POST /api/jobs/extract`` returns immediately and the UI polls
``GET /api/jobs/extract/status`` for a live stepper.

Built for large mailboxes (thousands of emails):
- **Time window**: only candidates within ``[since, until]`` are considered, so
  the first run doesn't scan everything.
- **Cheap-first ordering**: the free keyword pre-filter runs on subject + cached
  body only; emails that miss it are screened without any IMAP fetch or LLM call.
  Only keyword hits fetch their body (if missing) before classify.
- **Concurrency**: up to ``_CONCURRENCY`` emails run their (blocking) IMAP/LLM
  work in parallel via the threadpool. Workers touch only plain data — never the
  ORM session; DB writes are applied serially in the main coroutine per batch.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select

from .. import db, secrets_store
from ..models import Account, EmailMessage, JobApplication
from . import imap_sync, job_config, job_extractor, job_keywords
from .job_extractor import JobExtractionUnavailable

_BATCH_SIZE = 50
_CONCURRENCY = 5

# Progress stages surfaced to the UI (mapped to Chinese labels client-side).
STAGE_IDLE = ""
STAGE_KEYWORD = "keyword"
STAGE_CLASSIFY = "classify"
STAGE_EXTRACT = "extract"

# Overall phase: caching bodies first, then the scan/pipeline.
PHASE_IDLE = ""
PHASE_CACHE = "cache"
PHASE_SCAN = "scan"

_log = logging.getLogger("mail_agent.extract")


@dataclass
class ExtractState:
    running: bool = False
    phase: str = PHASE_IDLE
    total: int = 0
    current: int = 0
    stage: str = STAGE_IDLE
    created: int = 0
    done: bool = False
    error: str | None = None
    hint: str | None = None
    detail: str | None = None


_state = ExtractState()
_lock = asyncio.Lock()


def get_state() -> ExtractState:
    return _state


@dataclass
class _Item:
    """Plain snapshot of an email + its account creds — safe to use off-session."""

    id: int
    uid: str
    subject: str
    sender: str
    body: str
    host: str
    port: int
    use_ssl: bool
    username: str
    password: str | None


@dataclass
class _Result:
    email_id: int
    screen: int
    fetched_body: str | None = None
    company: str = ""
    position: str = ""
    applied_date: str = ""
    status_code: int = 0
    is_job: bool = False


def _to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    txt = s.strip().replace("Z", "+00:00")
    for candidate in (txt, f"{txt}T00:00:00"):
        try:
            dt = datetime.fromisoformat(candidate)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


async def _existing_status_index(
    session, cfg: job_config.JobsConfig
) -> dict[tuple[str, str], set[int]]:
    """Map each normalized (company, position) group to the set of status codes it
    already has a record for — the basis for same-stage dedup during a scan."""
    rows = (
        await session.execute(
            select(
                JobApplication.company, JobApplication.position, JobApplication.status_code
            )
        )
    ).all()
    index: dict[tuple[str, str], set[int]] = {}
    for company, position, status_code in rows:
        key = (cfg.company_key(company or "")[0], (position or "").strip().casefold())
        index.setdefault(key, set()).add(int(status_code))
    return index


async def start_extract(
    since: datetime | None = None, until: datetime | None = None
) -> bool:
    """Kick off extraction of unscreened candidates within [since, until] if none
    is running. Returns True if started."""
    global _state
    async with _lock:
        if _state.running:
            return False
        if not (job_extractor.classify_configured() and job_extractor.extract_configured()):
            _state = ExtractState(error=JobExtractionUnavailable().message, done=True)
            return False
        _state = ExtractState(running=True)
        asyncio.create_task(_run(_to_utc(since), _to_utc(until)))
        return True


def _candidate_filter(since: datetime | None, until: datetime | None):
    linked = select(JobApplication.email_id).where(JobApplication.email_id != 0)
    conds = [
        EmailMessage.job_screened == job_extractor.SCREEN_UNSCREENED,
        EmailMessage.id.notin_(linked),
    ]
    if since is not None:
        conds.append(EmailMessage.date >= since)
    if until is not None:
        conds.append(EmailMessage.date <= until)
    return conds


async def _run(since: datetime | None, until: datetime | None) -> None:
    try:
        async with db.get_sessionmaker()() as session:
            conds = _candidate_filter(since, until)
            scan_total = (
                await session.execute(select(func.count()).select_from(EmailMessage).where(*conds))
            ).scalar_one()

            accounts = {
                a.id: a for a in (await session.execute(select(Account))).scalars().all()
            }
            pw_cache: dict[int, str | None] = {}

            async def _password_for(acc_id: int) -> str | None:
                if acc_id not in pw_cache:
                    acc = accounts.get(acc_id)
                    pw_cache[acc_id] = (
                        await run_in_threadpool(secrets_store.get_imap_password, acc.credential_key)
                        if acc
                        else None
                    )
                return pw_cache[acc_id]

            # ── Phase 1: bulk-cache bodies of in-range candidates that have none,
            # so the keyword pre-filter + classifier see full content (not just the
            # subject). One login per account; bodies are cached for later reuse.
            await _cache_bodies(session, since, until, accounts, _password_for)

            # ── Phase 2: scan (keyword → classify → extract).
            _state.phase = PHASE_SCAN
            _state.stage = STAGE_IDLE
            _state.total = scan_total
            _state.current = 0

            cfg = job_config.load()
            # Same-stage dedup: index the (company, position) status codes that
            # already exist so a second email at a stage we've recorded (e.g. an
            # interview invite after "you advanced to interview") makes no new row.
            existing = await _existing_status_index(session, cfg)

            while True:
                # Re-query each round: screened rows drop out of the filter, so
                # this walks toward older mail until no candidates remain.
                batch = (
                    await session.execute(
                        select(EmailMessage)
                        .where(*_candidate_filter(since, until))
                        .order_by(EmailMessage.date.desc())
                        .limit(_BATCH_SIZE)
                    )
                ).scalars().all()
                if not batch:
                    break

                by_id = {e.id: e for e in batch}
                items: list[_Item] = []
                for e in batch:
                    acc = accounts.get(e.account_id)
                    items.append(
                        _Item(
                            id=e.id,
                            uid=e.uid,
                            subject=e.subject,
                            sender=e.from_address,
                            body=e.body_text or "",
                            host=acc.host if acc else "",
                            port=acc.port if acc else 993,
                            use_ssl=acc.use_ssl if acc else True,
                            username=acc.username if acc else "",
                            password=await _password_for(e.account_id),
                        )
                    )

                sem = asyncio.Semaphore(_CONCURRENCY)
                results = await asyncio.gather(*(_process_one(it, sem, cfg) for it in items))

                # Serial DB apply (workers never touch the session).
                for r in results:
                    email = by_id[r.email_id]
                    if r.fetched_body:
                        email.body_text = r.fetched_body
                    email.job_screened = r.screen
                    if r.screen != job_extractor.SCREEN_LINKED:
                        continue
                    group = (cfg.company_key(r.company)[0], (r.position or "").strip().casefold())
                    seen = existing.setdefault(group, set())
                    if r.status_code in seen:
                        # Duplicate of a stage we already track — screen it, no row.
                        email.job_screened = job_extractor.SCREEN_EXCLUDED
                        continue
                    seen.add(r.status_code)
                    applied = _parse_iso(r.applied_date) or email.date
                    session.add(
                        JobApplication(
                            company=r.company,
                            position=r.position,
                            applied_at=applied,
                            status_code=r.status_code,
                            email_id=email.id,
                            manually_edited=False,
                            timeline_json=json.dumps(
                                [{"status": r.status_code, "ts": applied.isoformat()}]
                            ),
                        )
                    )
                    _state.created += 1
                await session.commit()
                session.expunge_all()  # bound memory over large mailboxes

        _state.stage = STAGE_IDLE
        _state.phase = PHASE_IDLE
    except JobExtractionUnavailable as e:
        _state.error = e.message
    except Exception as e:  # noqa: BLE001 — surface any provider/DB error to the UI
        _state.error = "求职抽取失败，请检查模型配置或稍后重试。"
        _state.detail = f"{type(e).__name__}: {e}"
        _log.warning("Extraction failed", exc_info=True)
    finally:
        _state.running = False
        _state.done = True


async def _cache_bodies(session, since, until, accounts, password_for) -> None:
    """Phase 1: fetch + cache bodies of in-range candidates that have none yet.

    Fetches per account in a single login (``imap_sync.fetch_bodies``) and works
    in id-chunks so memory stays bounded on large mailboxes. Emails whose body
    can't be fetched keep an empty body (the scan then falls back to subject-only
    keyword matching for them).
    """
    ids = (
        await session.execute(
            select(EmailMessage.id)
            .where(*_candidate_filter(since, until), func.coalesce(EmailMessage.body_text, "") == "")
            .order_by(EmailMessage.date.desc())
        )
    ).scalars().all()

    _state.phase = PHASE_CACHE
    _state.total = len(ids)
    _state.current = 0
    if not ids:
        return

    for i in range(0, len(ids), _BATCH_SIZE):
        chunk = ids[i : i + _BATCH_SIZE]
        rows = (
            await session.execute(select(EmailMessage).where(EmailMessage.id.in_(chunk)))
        ).scalars().all()

        by_acc: dict[int, list] = {}
        for e in rows:
            by_acc.setdefault(e.account_id, []).append(e)

        for acc_id, group in by_acc.items():
            acc = accounts.get(acc_id)
            password = await password_for(acc_id)
            if not (acc and password):
                continue
            uids = [str(e.uid) for e in group]
            bodies = await run_in_threadpool(
                imap_sync.fetch_bodies,
                acc.host,
                acc.port,
                acc.use_ssl,
                acc.username,
                password,
                uids,
            )
            for e in group:
                body = bodies.get(str(e.uid))
                if body:
                    e.body_text = body

        await session.commit()
        _state.current += len(chunk)
        session.expunge_all()  # release cached bodies from the identity map


async def _process_one(
    item: _Item, sem: asyncio.Semaphore, cfg: job_config.JobsConfig
) -> _Result:
    """Pure-data pipeline for one email; no ORM/session access (concurrency-safe)."""
    async with sem:
        try:
            # Stage 0 — keyword pre-filter on subject + cached body (free, no IMAP).
            _state.stage = STAGE_KEYWORD
            if not job_keywords.looks_like_candidate(item.subject, item.body, cfg):
                return _Result(item.id, job_extractor.SCREEN_NOT_JOB)

            body = item.body
            fetched: str | None = None
            if not body and item.username and item.password:
                body = await run_in_threadpool(
                    imap_sync.fetch_body,
                    item.host,
                    item.port,
                    item.use_ssl,
                    item.username,
                    item.password,
                    item.uid,
                )
                fetched = body

            # Exclusion rules (e.g. a Google Meet invite that just duplicates the
            # "you advanced to interview" email) — screened, no record created.
            if cfg.is_excluded(subject=item.subject, sender=item.sender, body=body or ""):
                return _Result(item.id, job_extractor.SCREEN_EXCLUDED, fetched_body=fetched)

            # Stage 1 — cheap model binary classify.
            _state.stage = STAGE_CLASSIFY
            is_job = await run_in_threadpool(
                job_extractor.classify_is_job,
                subject=item.subject,
                sender=item.sender,
                body=body or "",
            )
            if not is_job:
                return _Result(item.id, job_extractor.SCREEN_NOT_JOB, fetched_body=fetched)

            # Stage 2 — strong model structured extraction.
            _state.stage = STAGE_EXTRACT
            res = await run_in_threadpool(
                job_extractor.extract,
                subject=item.subject,
                sender=item.sender,
                body=body or "",
            )
            if res.is_job and res.company:
                return _Result(
                    item.id,
                    job_extractor.SCREEN_LINKED,
                    fetched_body=fetched,
                    company=res.company,
                    position=res.position,
                    applied_date=res.applied_date,
                    status_code=res.status_code,
                    is_job=True,
                )
            return _Result(item.id, job_extractor.SCREEN_NOT_JOB, fetched_body=fetched)
        finally:
            _state.current += 1
