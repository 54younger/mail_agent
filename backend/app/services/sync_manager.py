"""Background sync orchestration + in-memory progress.

Runs the blocking IMAP header fetch in a threadpool, then upserts rows by UID
(never duplicating). Progress is polled by the frontend via GET /api/sync/status.
Single-user app → a single module-level state object is sufficient.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy import update as sa_update

from .. import db, secrets_store
from ..core.errors import ImapErrorKind, classify_imap_error, error_info
from ..models import Account, EmailMessage
from . import imap_sync

INCREMENTAL_LIMIT = 100


@dataclass
class SyncState:
    running: bool = False
    fetched: int = 0
    total: int = 0
    done: bool = False
    error: str | None = None
    hint: str | None = None
    kind: str | None = None


_state = SyncState()
_lock = asyncio.Lock()


def get_state() -> SyncState:
    return _state


async def _load_account() -> Account | None:
    async with db.get_sessionmaker()() as session:
        res = await session.execute(select(Account).limit(1))
        return res.scalar_one_or_none()


async def start_sync(*, full: bool) -> bool:
    """Kick off a sync if none is running. Returns True if started."""
    global _state
    async with _lock:
        if _state.running:
            return False
        acc = await _load_account()
        if acc is None:
            _state = SyncState(error="尚未绑定邮箱账户", kind=ImapErrorKind.UNKNOWN.value)
            return False
        _state = SyncState(running=True)
        asyncio.create_task(
            _run(acc.id, acc.host, acc.port, acc.use_ssl, acc.username, acc.credential_key, full)
        )
        return True


def _fail_from_exception(exc: object) -> None:
    info = error_info(classify_imap_error(exc))
    _state.error = info.message
    _state.hint = info.hint
    _state.kind = info.kind.value


async def _run(
    acc_id: int,
    host: str,
    port: int,
    use_ssl: bool,
    username: str,
    credential_key: str,
    full: bool,
) -> None:
    try:
        password = await run_in_threadpool(secrets_store.get_imap_password, credential_key)
        if not password:
            info = error_info(ImapErrorKind.AUTH_FAILED)
            _state.error, _state.hint, _state.kind = info.message, info.hint, info.kind.value
            return

        def progress(fetched: int, total: int) -> None:
            _state.fetched = fetched
            _state.total = total

        rows, total, uidvalidity = await run_in_threadpool(
            imap_sync.fetch_headers,
            host,
            port,
            use_ssl,
            username,
            password,
            full=full,
            limit=INCREMENTAL_LIMIT,
            progress=progress,
        )

        async with db.get_sessionmaker()() as session:
            await _upsert(session, rows)
            await session.execute(
                sa_update(Account)
                .where(Account.id == acc_id)
                .values(last_sync_at=datetime.now(timezone.utc), uid_validity=uidvalidity)
            )
            await session.commit()

        if total:
            _state.total = total if full else min(INCREMENTAL_LIMIT, total)
        _state.fetched = len(rows)
        _state.done = True
    except Exception as e:  # noqa: BLE001 — surface any IMAP/DB failure to the UI
        _fail_from_exception(e)
    finally:
        _state.running = False


async def _upsert(session, rows: list[imap_sync.EmailRow], folder: str = "INBOX") -> None:
    """Insert new messages, update metadata on known UIDs (preserving cached
    body_text/translation). Mirrors the Dart upsert-by-uid behavior."""
    if not rows:
        return
    existing = await session.execute(
        select(EmailMessage.id, EmailMessage.uid).where(EmailMessage.folder == folder)
    )
    id_by_uid = {uid: eid for eid, uid in existing.all()}

    for r in rows:
        eid = id_by_uid.get(r.uid)
        if eid is not None:
            await session.execute(
                sa_update(EmailMessage)
                .where(EmailMessage.id == eid)
                .values(
                    from_address=r.from_address,
                    to_addresses=r.to_addresses,
                    subject=r.subject,
                    date=r.date,
                )
            )
        else:
            session.add(
                EmailMessage(
                    uid=r.uid,
                    folder=folder,
                    from_address=r.from_address,
                    to_addresses=r.to_addresses,
                    subject=r.subject,
                    date=r.date,
                    body_text="",
                )
            )
