"""Background sync orchestration + in-memory progress.

Syncs every bound account in turn: runs the blocking IMAP header fetch in a
threadpool, then upserts rows by (account_id, UID) so re-syncing never duplicates.
Progress (polled via GET /api/sync/status) aggregates across accounts. A failure
on one account is recorded but doesn't stop the others.
"""

from __future__ import annotations

import asyncio
import logging
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

_log = logging.getLogger("mail_agent.sync")


@dataclass
class SyncState:
    running: bool = False
    fetched: int = 0
    total: int = 0
    done: bool = False
    error: str | None = None
    hint: str | None = None
    kind: str | None = None
    # Raw error text ("<ExcType>: <msg>") for diagnostics — shown in the UI.
    detail: str | None = None


_state = SyncState()
_lock = asyncio.Lock()


def get_state() -> SyncState:
    return _state


async def _load_account_snapshots() -> list[tuple]:
    async with db.get_sessionmaker()() as session:
        accounts = (await session.execute(select(Account).order_by(Account.id))).scalars().all()
        return [
            (a.id, a.host, a.port, a.use_ssl, a.username, a.credential_key) for a in accounts
        ]


async def start_sync(*, full: bool) -> bool:
    """Kick off a sync of all accounts if none is running. Returns True if started."""
    global _state
    async with _lock:
        if _state.running:
            return False
        snaps = await _load_account_snapshots()
        if not snaps:
            _state = SyncState(error="尚未绑定邮箱账户", kind=ImapErrorKind.UNKNOWN.value)
            return False
        _state = SyncState(running=True)
        asyncio.create_task(_run_all(snaps, full))
        return True


async def _run_all(snaps: list[tuple], full: bool) -> None:
    fetched_base = 0
    total_base = 0
    last_error = None
    last_detail = None
    try:
        for acc_id, host, port, use_ssl, username, credential_key in snaps:
            try:
                password = await run_in_threadpool(
                    secrets_store.get_imap_password, credential_key
                )
                if not password:
                    last_error = error_info(ImapErrorKind.AUTH_FAILED)
                    continue

                # Bind the running offsets as defaults so this closure captures
                # this iteration's base rather than the loop's mutating values.
                def progress(
                    fetched: int, total: int, *, _fb: int = fetched_base, _tb: int = total_base
                ) -> None:
                    _state.fetched = _fb + fetched
                    _state.total = _tb + total

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
                    await _upsert(session, acc_id, rows)
                    await session.execute(
                        sa_update(Account)
                        .where(Account.id == acc_id)
                        .values(
                            last_sync_at=datetime.now(timezone.utc), uid_validity=uidvalidity
                        )
                    )
                    await session.commit()

                fetched_base += len(rows)
                total_base += total if full else min(INCREMENTAL_LIMIT, total)
                _state.fetched = fetched_base
                _state.total = total_base
            except Exception as e:  # noqa: BLE001 — record and continue with other accounts
                last_error = error_info(classify_imap_error(e))
                last_detail = f"[{username}] {type(e).__name__}: {e}"
                _log.warning("Sync failed for %s", username, exc_info=True)

        if last_error is not None:
            _state.error = last_error.message
            _state.hint = last_error.hint
            _state.kind = last_error.kind.value
            _state.detail = last_detail
        _state.done = True
    finally:
        _state.running = False


async def _upsert(
    session, account_id: int, rows: list[imap_sync.EmailRow], folder: str = "INBOX"
) -> None:
    """Insert new messages, update metadata on known UIDs (preserving cached
    body_text/translation). Keyed by (account_id, folder, uid)."""
    if not rows:
        return
    existing = await session.execute(
        select(EmailMessage.id, EmailMessage.uid).where(
            EmailMessage.account_id == account_id, EmailMessage.folder == folder
        )
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
                    account_id=account_id,
                    uid=r.uid,
                    folder=folder,
                    from_address=r.from_address,
                    to_addresses=r.to_addresses,
                    subject=r.subject,
                    date=r.date,
                    body_text="",
                )
            )
