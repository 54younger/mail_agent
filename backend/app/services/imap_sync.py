"""IMAP connection, header sync, and body fetch via ``imap-tools``.

These are **blocking** functions (imap-tools is synchronous) intended to be run
in a threadpool from the async routers. They are deliberately free of DB/ORM code
so they stay easy to unit-test with a fake mailbox — the caller persists the
returned row dicts.

Ported quirks from the Flutter app:
- **163/126/yeah.net** reject SELECT with "Unsafe Login" unless the client sends
  the RFC 2971 ``ID`` command after LOGIN and *before* SELECT. We log in with
  ``initial_folder=None`` (no auto-select), send ID, then select INBOX.
- Using imap-tools (which builds correct parenthesized FETCHes and MIME-decodes
  envelopes) sidesteps the raw-FETCH metadata bug that plagued the Dart version.
"""

from __future__ import annotations

import imaplib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from imap_tools import AND, MailBox, MailBoxUnencrypted

from ..core.errors import ImapErrorInfo, classify_imap_error, error_info

# Python's stdlib imaplib does NOT know the RFC 2971 ID command, so
# ``_simple_command("ID", ...)`` raises KeyError (Commands["ID"]) and never sends
# anything. Register it here (valid before/after auth) so we can actually
# transmit ID — 163/126/yeah.net reject SELECT with "Unsafe Login" without it.
if "ID" not in imaplib.Commands:
    imaplib.Commands["ID"] = ("NONAUTH", "AUTH", "SELECTED")

# Sent via the IMAP ID command. 163 requires this before SELECT.
_CLIENT_ID = {"name": "Mail Agent", "version": "1.0"}

# Chunk size for bulk header fetches (efficiency without loading everything).
_BULK = 200


@dataclass
class EmailRow:
    uid: str
    folder: str
    from_address: str
    to_addresses: str
    subject: str
    date: datetime


def _send_id(client) -> None:
    """Best-effort RFC 2971 ID. Non-fatal: providers without ID support ignore it."""
    try:
        args = []
        for k, v in _CLIENT_ID.items():
            args.append(f'"{k}"')
            args.append(f'"{v}"')
        typ, dat = client._simple_command("ID", "(" + " ".join(args) + ")")
        client._untagged_response(typ, dat, "ID")
    except Exception:
        pass


def _open(
    host: str, port: int, use_ssl: bool, username: str, password: str
) -> MailBox:
    """Connect + login + ID + SELECT INBOX. Raises on any failure (caller
    classifies)."""
    box = MailBox(host, port) if use_ssl else MailBoxUnencrypted(host, port)
    # initial_folder=None → don't auto-SELECT, so we can inject ID first.
    box.login(username, password, initial_folder=None)
    _send_id(box.client)
    box.folder.set("INBOX")
    return box


def _coerce_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_row(msg, folder: str) -> EmailRow | None:
    uid = msg.uid
    if not uid:
        return None
    return EmailRow(
        uid=str(uid),
        folder=folder,
        from_address=msg.from_ or "",
        to_addresses=",".join(msg.to) if msg.to else "",
        subject=msg.subject or "",
        date=_coerce_utc(msg.date),
    )


def test_connection(
    host: str, port: int, use_ssl: bool, username: str, password: str
) -> ImapErrorInfo | None:
    """Return ``None`` on success, or an :class:`ImapErrorInfo` describing the
    failure. Selects INBOX so provider-level blocks (163 "Unsafe Login") surface
    at bind time."""
    box = None
    try:
        box = _open(host, port, use_ssl, username, password)
        return None
    except Exception as e:  # noqa: BLE001 — classify anything the lib/socket raises
        return error_info(classify_imap_error(e))
    finally:
        if box is not None:
            try:
                box.logout()
            except Exception:
                pass


def fetch_headers(
    host: str,
    port: int,
    use_ssl: bool,
    username: str,
    password: str,
    *,
    full: bool,
    limit: int,
    progress: Callable[[int, int], None] | None = None,
) -> tuple[list[EmailRow], int, int]:
    """Fetch message headers newest-first.

    - ``full=True``: all messages (progress reported as they stream in).
    - ``full=False``: only the newest ``limit`` (incremental refresh).

    Returns ``(rows, total_in_mailbox, uidvalidity)``.
    """
    box = None
    try:
        box = _open(host, port, use_ssl, username, password)
        status = box.folder.status("INBOX", options=["MESSAGES", "UIDVALIDITY"])
        total = int(status.get("MESSAGES", 0))
        uidvalidity = int(status.get("UIDVALIDITY", 0))

        if total == 0:
            return [], 0, uidvalidity

        want = total if full else min(limit, total)
        if progress:
            progress(0, want)

        rows: list[EmailRow] = []
        fetched = 0
        for msg in box.fetch(
            "ALL",
            reverse=True,  # newest first
            limit=want,
            mark_seen=False,
            headers_only=True,
            bulk=_BULK,
        ):
            row = _to_row(msg, "INBOX")
            fetched += 1
            if row is not None:
                rows.append(row)
            if progress and fetched % 20 == 0:
                progress(fetched, want)

        if progress:
            progress(want, want)
        return rows, total, uidvalidity
    finally:
        if box is not None:
            try:
                box.logout()
            except Exception:
                pass


def fetch_body(
    host: str,
    port: int,
    use_ssl: bool,
    username: str,
    password: str,
    uid: str,
) -> str:
    """Fetch a single message body by UID, preferring HTML. Best-effort: returns
    "" on any failure."""
    box = None
    try:
        box = _open(host, port, use_ssl, username, password)
        for msg in box.fetch(AND(uid=str(uid)), mark_seen=False, bulk=False):
            html = (msg.html or "").strip()
            body = html if html else (msg.text or "")
            cap = 500_000
            return body[:cap]
        return ""
    except Exception:
        return ""
    finally:
        if box is not None:
            try:
                box.logout()
            except Exception:
                pass
