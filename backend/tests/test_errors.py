"""Parity tests for the ported IMAP error taxonomy (was imap_error.dart)."""

from __future__ import annotations

import pytest

from app.core.errors import (
    ImapError,
    ImapErrorKind,
    classify_imap_error,
    error_info,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("SELECT Unsafe Login. Please contact kefu@188.com", ImapErrorKind.ACCOUNT_LOCKED),
        ("Account locked for security", ImapErrorKind.ACCOUNT_LOCKED),
        ("[AUTHENTICATIONFAILED] Invalid credentials", ImapErrorKind.AUTH_FAILED),
        ("LOGIN Failed: incorrect password", ImapErrorKind.AUTH_FAILED),
        ("IMAP service is disabled for this account", ImapErrorKind.IMAP_DISABLED),
        ("[NOPERM] access denied", ImapErrorKind.IMAP_DISABLED),
        ("SSL handshake failed: certificate verify", ImapErrorKind.TLS_ERROR),
        ("Connection timed out", ImapErrorKind.NETWORK_ERROR),
        ("getaddrinfo failed: no such host", ImapErrorKind.NETWORK_ERROR),
        ("Service temporarily unavailable, try again later", ImapErrorKind.SERVER_ERROR),
        ("Too many simultaneous connections", ImapErrorKind.SERVER_ERROR),
        ("something entirely unexpected", ImapErrorKind.UNKNOWN),
    ],
)
def test_classify(raw: str, expected: ImapErrorKind) -> None:
    assert classify_imap_error(Exception(raw)) is expected


def test_error_info_retry_and_resetup() -> None:
    net = error_info(ImapErrorKind.NETWORK_ERROR)
    assert net.can_retry is True
    assert net.should_resetup is False

    auth = error_info(ImapErrorKind.AUTH_FAILED)
    assert auth.can_retry is False
    assert auth.should_resetup is True
    assert "授权码" in auth.hint  # Chinese guidance preserved from the Dart version


def test_error_info_has_message_for_every_kind() -> None:
    for kind in ImapErrorKind:
        info = error_info(kind)
        assert info.message
        assert info.hint


def test_imap_error_from_exception() -> None:
    err = ImapError.from_exception(Exception("SELECT Unsafe Login"))
    assert err.info.kind is ImapErrorKind.ACCOUNT_LOCKED
    assert str(err) == err.info.message
