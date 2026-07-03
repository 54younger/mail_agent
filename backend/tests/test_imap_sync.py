"""Unit tests for the IMAP sync helpers with a fake mailbox — no network."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services import imap_sync


class FakeMsg:
    def __init__(self, uid, from_, to, subject, date):
        self.uid = uid
        self.from_ = from_
        self.to = to
        self.subject = subject
        self.date = date


def test_to_row_maps_fields_and_coerces_utc():
    naive = datetime(2026, 6, 15, 9, 0, 0)  # no tzinfo
    row = imap_sync._to_row(
        FakeMsg("101", "hr@corp.com", ("me@x.com", "cc@x.com"), "你好", naive), "INBOX"
    )
    assert row is not None
    assert row.uid == "101"
    assert row.from_address == "hr@corp.com"
    assert row.to_addresses == "me@x.com,cc@x.com"
    assert row.subject == "你好"
    assert row.date.tzinfo is not None
    assert row.date == naive.replace(tzinfo=timezone.utc)


def test_to_row_skips_missing_uid():
    assert imap_sync._to_row(FakeMsg(None, "a@b.com", (), "s", datetime.now()), "INBOX") is None


def test_send_id_is_non_fatal():
    class BadClient:
        def _simple_command(self, *a):
            raise RuntimeError("boom")

    # Should swallow the error, not raise.
    imap_sync._send_id(BadClient())


def test_imaplib_knows_id_command():
    # Importing imap_sync must register the RFC 2971 ID command in imaplib, else
    # _simple_command("ID", ...) raises KeyError and never sends (163 blocks).
    import imaplib

    assert "ID" in imaplib.Commands
    assert "AUTH" in imaplib.Commands["ID"]


def test_send_id_transmits_the_id_command():
    class RecordingClient:
        def __init__(self):
            self.sent = None

        def _simple_command(self, name, arg):
            self.sent = (name, arg)
            return ("OK", [b""])

        def _untagged_response(self, typ, dat, name):
            return (typ, [])

    client = RecordingClient()
    imap_sync._send_id(client)
    assert client.sent == ("ID", '("name" "Mail Agent" "version" "1.0")')


@pytest.mark.parametrize("full,limit,total,expected_want", [(True, 100, 5, 5), (False, 3, 5, 3)])
def test_fetch_headers_limits(monkeypatch, full, limit, total, expected_want):
    """fetch_headers should request `total` when full, else `min(limit, total)`."""
    captured = {}

    class FakeClient:
        untagged_responses = {"UIDVALIDITY": [b"42"]}

    class FakeBox:
        def __init__(self):
            self.client = FakeClient()

        def uids(self, *a, **k):
            return [str(1000 + i) for i in range(total)]

        def fetch(self, criteria, reverse, limit, mark_seen, headers_only, bulk):
            captured["limit"] = limit
            base = datetime(2026, 6, 1, tzinfo=timezone.utc)
            for i in range(limit):
                yield FakeMsg(str(1000 + i), "hr@corp.com", ("me@x.com",), f"s{i}", base)

        def logout(self):
            pass

    monkeypatch.setattr(imap_sync, "_open", lambda *a, **k: FakeBox())

    rows, got_total, uidvalidity = imap_sync.fetch_headers(
        "h", 993, True, "u", "p", full=full, limit=limit
    )
    assert got_total == total
    assert uidvalidity == 42
    assert captured["limit"] == expected_want
    assert len(rows) == expected_want
