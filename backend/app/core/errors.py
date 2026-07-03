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
    ImapErrorKind.AUTH_FAILED: "密码或授权码错误",
    ImapErrorKind.IMAP_DISABLED: "IMAP 服务未启用",
    ImapErrorKind.ACCOUNT_LOCKED: "账户登录被安全拦截",
    ImapErrorKind.NETWORK_ERROR: "网络连接失败",
    ImapErrorKind.TLS_ERROR: "SSL 加密连接失败",
    ImapErrorKind.SERVER_ERROR: "邮件服务器暂时不可用",
    ImapErrorKind.UNKNOWN: "同步失败",
}

_HINT: dict[ImapErrorKind, str] = {
    ImapErrorKind.AUTH_FAILED: (
        "163、QQ、Gmail 等邮箱需使用「授权码」而非登录密码。\n"
        "请在网页版邮箱 → 设置 → 账户安全 → 开启 IMAP → 生成授权码，然后重新绑定。"
    ),
    ImapErrorKind.IMAP_DISABLED: (
        "请在网页版邮箱开启 IMAP 服务：\n"
        "设置 → POP3/SMTP/IMAP → 开启 IMAP 服务，再重新绑定账号。"
    ),
    ImapErrorKind.ACCOUNT_LOCKED: (
        "163/QQ 邮箱检测到新设备登录，已触发安全保护。\n"
        "请登录网页版邮箱完成安全验证，或改用「授权码」代替密码后重新绑定。"
    ),
    ImapErrorKind.NETWORK_ERROR: "请检查网络连接，并确认防火墙未屏蔽 IMAP 端口（993）。",
    ImapErrorKind.TLS_ERROR: (
        "请确认未使用拦截 HTTPS 流量的代理或企业防火墙，或切换至其他网络后重试。"
    ),
    ImapErrorKind.SERVER_ERROR: "邮件服务器临时故障，请等待几分钟后点击「重试」。",
    ImapErrorKind.UNKNOWN: "请检查邮箱地址、密码和服务器配置是否正确，或重新绑定账号。",
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
