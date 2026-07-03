"""Secret storage for the IMAP password and Claude API key.

Strategy (in order):
1. **OS keyring** (Windows Credential Manager / macOS Keychain / Secret Service) —
   the same posture as the old ``flutter_secure_storage``.
2. **Fernet-encrypted file** in the data folder, used automatically when no OS
   keyring backend is available (headless Linux, some WSL/Docker setups). The
   Fernet key lives in ``<data_dir>/.secret.key`` with 0600 perms.

Either way, secrets never touch the SQLite DB or git. Callers use the simple
get/set/delete helpers and don't care which backend is active.
"""

from __future__ import annotations

import json
import os
import stat

from . import config

_SERVICE = "mail_agent"
_CLAUDE_KEY = "claude_api_key"

# Force the file backend (tests, headless). Otherwise keyring is tried first.
_ENV_FORCE_FILE = "MAIL_AGENT_SECRETS_FILE_BACKEND"


def imap_credential_key(username: str, host: str) -> str:
    return f"imap::{username}::{host}"


# ── Backend selection ────────────────────────────────────────────────────────


_keyring_ok: bool | None = None


def _keyring_available() -> bool:
    """True only if the OS keyring actually round-trips a value.

    Merely having a non-``fail`` backend isn't enough: on WSL/headless the
    Secret Service backend is reported but has no running daemon, so set/get
    fails or doesn't persist — which caused credentials to vanish on restart.
    We probe with a real set→get→delete (cached) and fall back to the encrypted
    file store otherwise, so bindings always survive a restart.
    """
    global _keyring_ok
    if os.environ.get(_ENV_FORCE_FILE):
        return False
    if _keyring_ok is not None:
        return _keyring_ok
    try:
        import keyring

        probe = "__mailagent_probe__"
        keyring.set_password(_SERVICE, probe, "1")
        ok = keyring.get_password(_SERVICE, probe) == "1"
        try:
            keyring.delete_password(_SERVICE, probe)
        except Exception:
            pass
        _keyring_ok = bool(ok)
    except Exception:
        _keyring_ok = False
    return _keyring_ok


# ── Encrypted-file backend ───────────────────────────────────────────────────


def _key_path():
    return config.get_data_dir() / ".secret.key"  # type: ignore[union-attr]


def _store_path():
    return config.get_data_dir() / ".secrets.enc"  # type: ignore[union-attr]


def _fernet():
    from cryptography.fernet import Fernet

    kp = _key_path()
    if kp.exists():
        key = kp.read_bytes()
    else:
        key = Fernet.generate_key()
        kp.write_bytes(key)
        os.chmod(kp, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    return Fernet(key)


def _file_read_all() -> dict[str, str]:
    sp = _store_path()
    if not sp.exists():
        return {}
    try:
        raw = _fernet().decrypt(sp.read_bytes())
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def _file_write_all(data: dict[str, str]) -> None:
    sp = _store_path()
    token = _fernet().encrypt(json.dumps(data).encode("utf-8"))
    sp.write_bytes(token)
    os.chmod(sp, stat.S_IRUSR | stat.S_IWUSR)  # 0600


# ── Public API ───────────────────────────────────────────────────────────────


def set_secret(key: str, value: str) -> None:
    if _keyring_available():
        import keyring

        keyring.set_password(_SERVICE, key, value)
        return
    data = _file_read_all()
    data[key] = value
    _file_write_all(data)


def get_secret(key: str) -> str | None:
    if _keyring_available():
        import keyring

        return keyring.get_password(_SERVICE, key)
    return _file_read_all().get(key)


def delete_secret(key: str) -> None:
    if _keyring_available():
        import keyring

        try:
            keyring.delete_password(_SERVICE, key)
        except Exception:
            pass
        return
    data = _file_read_all()
    if key in data:
        del data[key]
        _file_write_all(data)


# Convenience wrappers used across the app.


def set_imap_password(username: str, host: str, password: str) -> str:
    key = imap_credential_key(username, host)
    set_secret(key, password)
    return key


def get_imap_password(credential_key: str) -> str | None:
    return get_secret(credential_key)


def delete_imap_password(credential_key: str) -> None:
    delete_secret(credential_key)


def set_claude_key(value: str) -> None:
    set_secret(_CLAUDE_KEY, value)


def get_claude_key() -> str | None:
    return get_secret(_CLAUDE_KEY)
