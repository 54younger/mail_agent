"""IMAP error classification + user-facing Chinese messages.

Direct port of the Flutter ``lib/core/imap_error.dart`` taxonomy so the web UI
gives the same actionable guidance (163/QQ/Gmail auth-code hints, etc.). Kept as
pure functions/data so it is trivially unit-testable and reusable by the setup
and sync endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ImapErrorKind(str, Enum):
    AUTH_FAILED = "auth_failed"
    IMAP_DISABLED = "imap_disabled"
    ACCOUNT_LOCKED = "account_locked"
    NETWORK_ERROR = "network_error"
    TLS_ERROR = "tls_error"
    SERVER_ERROR = "server_error"
    UNKNOWN = "unknown"


def classify_imap_error(exc: object) -> ImapErrorKind:
    """Map a raw IMAP/socket exception to an :class:`ImapErrorKind` by matching
    on the lowercased exception string (same heuristics as the Dart version)."""
    s = str(exc).lower()

    # Security block before/after auth — 163/QQ "Unsafe Login", suspended accounts.
    if any(
        t in s
        for t in ("unsafe login", "account locked", "login disabled", "account suspended")
    ):
        return ImapErrorKind.ACCOUNT_LOCKED

    # Wrong password / wrong auth code.
    if any(
        t in s
        for t in (
            "login failed",
            "authentication failed",
            "invalid credentials",
            "invalid login",
            "[authenticationfailed]",
            "incorrect password",
        )
    ):
        return ImapErrorKind.AUTH_FAILED

    # IMAP not enabled on the provider side.
    if "[noperm]" in s or (
        "imap" in s and any(t in s for t in ("disabled", "not enabled", "not opened"))
    ):
        return ImapErrorKind.IMAP_DISABLED

    # SSL / TLS handshake failure.
    if any(t in s for t in ("ssl", "tls", "certificate", "handshake")):
        return ImapErrorKind.TLS_ERROR

    # Network / socket errors.
    if any(
        t in s
        for t in (
            "connection refused",
            "connection timed out",
            "connection reset",
            "timeout",
            "socket",
            "no such host",
            "host unreachable",
            "network is unreachable",
            "getaddrinfo",
            "name or service not known",
            "name resolution",
            "temporary failure in name resolution",
            "nodename nor servname",
            "dns",
        )
    ):
        return ImapErrorKind.NETWORK_ERROR

    # Server overloaded / rate-limited / temporary.
    if any(
        t in s
        for t in (
            "unavailable",
            "too many",
            "rate limit",
            "try again later",
            "service not available",
        )
    ):
        return ImapErrorKind.SERVER_ERROR

    return ImapErrorKind.UNKNOWN


_USER_MESSAGE: dict[ImapErrorKind, str] = {
    ImapErrorKind.AUTH_FAILED: "Wrong password or app auth code",
    ImapErrorKind.IMAP_DISABLED: "IMAP access is not enabled",
    ImapErrorKind.ACCOUNT_LOCKED: "Sign-in blocked by the provider's security check",
    ImapErrorKind.NETWORK_ERROR: "Network connection failed",
    ImapErrorKind.TLS_ERROR: "SSL/TLS connection failed",
    ImapErrorKind.SERVER_ERROR: "Mail server is temporarily unavailable",
    ImapErrorKind.UNKNOWN: "Sync failed",
}

_HINT: dict[ImapErrorKind, str] = {
    ImapErrorKind.AUTH_FAILED: (
        "Providers like 163, QQ, and Gmail require an app-specific auth code, "
        "not your login password.\n"
        "In your mailbox's web settings → Account security → enable IMAP → "
        "generate an auth code, then connect again."
    ),
    ImapErrorKind.IMAP_DISABLED: (
        "Enable IMAP in your mailbox's web settings:\n"
        "Settings → POP3/SMTP/IMAP → turn on IMAP, then connect the account again."
    ),
    ImapErrorKind.ACCOUNT_LOCKED: (
        "163/QQ detected a sign-in from a new device and triggered a security block.\n"
        "Complete the security verification in the mailbox's web interface, or "
        "switch to an app-specific auth code instead of your password, then connect again."
    ),
    ImapErrorKind.NETWORK_ERROR: (
        "Check your network connection and make sure a firewall isn't blocking "
        "the IMAP port (993)."
    ),
    ImapErrorKind.TLS_ERROR: (
        "Make sure you're not behind a proxy or corporate firewall that intercepts "
        "HTTPS traffic, or switch to another network and try again."
    ),
    ImapErrorKind.SERVER_ERROR: (
        "The mail server is having a temporary problem. Wait a few minutes and click Retry."
    ),
    ImapErrorKind.UNKNOWN: (
        "Check that the email address, password, and server settings are correct, "
        "or connect the account again."
    ),
}


@dataclass(frozen=True)
class ImapErrorInfo:
    kind: ImapErrorKind
    message: str
    hint: str
    can_retry: bool
    should_resetup: bool


def error_info(kind: ImapErrorKind) -> ImapErrorInfo:
    can_retry = kind in (ImapErrorKind.NETWORK_ERROR, ImapErrorKind.SERVER_ERROR)
    return ImapErrorInfo(
        kind=kind,
        message=_USER_MESSAGE[kind],
        hint=_HINT[kind],
        can_retry=can_retry,
        should_resetup=not can_retry,
    )


class ImapError(Exception):
    """Wraps a classified IMAP failure for the API layer to serialize."""

    def __init__(self, info: ImapErrorInfo):
        super().__init__(info.message)
        self.info = info

    @classmethod
    def from_exception(cls, exc: object) -> "ImapError":
        return cls(error_info(classify_imap_error(exc)))
