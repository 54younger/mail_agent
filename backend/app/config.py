"""Data-folder resolution + non-secret settings.

The app is single-user and self-hosted: on first run the user picks a *data
folder* that holds their SQLite DB and a ``settings.json`` of non-secret prefs.
Because the choice of folder must survive restarts, a tiny bootstrap pointer
(``config.json``) is stored in the OS per-user config dir and records the chosen
path. Secrets (IMAP password, Claude key) never live here — they go to the OS
keyring (see ``secrets_store``).
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

APP_NAME = "mail_agent"

# Env override is handy for tests and Docker.
_ENV_DATA_DIR = "MAIL_AGENT_DATA_DIR"

_DEFAULT_SETTINGS: dict[str, object] = {
    "translation_target": "en",
    "auto_refresh_enabled": True,
    "auto_refresh_minutes": 15,
}

# Data files copied when the user moves their data folder (see change_data_dir).
_MIGRATE_FILES = ("app.sqlite", "settings.json", ".secrets.enc", ".secret.key")


def _bootstrap_config_path() -> Path:
    """Path to the small pointer file recording the chosen data folder."""
    return Path(user_config_dir(APP_NAME, appauthor=False)) / "config.json"


def default_data_dir() -> Path:
    """Sensible per-user default so the app works on first launch without a
    forced setup prompt (e.g. ``~/.local/share/mail_agent`` on Linux)."""
    return Path(user_data_dir(APP_NAME, appauthor=False))


def get_data_dir() -> Path | None:
    """Return the data folder to use. Never ``None`` in normal operation: an
    explicit env override wins (tests/Docker); otherwise the recorded folder from
    first-run/settings; otherwise the per-user default so the app is usable
    immediately."""
    env = os.environ.get(_ENV_DATA_DIR)
    if env:
        return Path(env).expanduser()

    pointer = _bootstrap_config_path()
    if not pointer.exists():
        return default_data_dir()
    try:
        raw = json.loads(pointer.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default_data_dir()
    path = raw.get("data_dir")
    return Path(path) if path else default_data_dir()


def is_configured() -> bool:
    return get_data_dir() is not None


_WIN_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")


def _running_on_wsl() -> bool:
    if platform.system() != "Linux":
        return False
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def _looks_like_windows_path(raw: str) -> bool:
    return bool(_WIN_PATH_RE.match(raw)) or raw.startswith("\\\\")


def _windows_to_wsl(raw: str) -> str:
    """Translate a Windows path (e.g. ``C:\\Users\\me\\Data``) to its WSL mount
    (``/mnt/c/Users/me/Data``). Uses the ``wslpath`` tool when available and
    falls back to a manual drive-letter rewrite."""
    try:
        out = subprocess.run(
            ["wslpath", "-u", raw], capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    m = re.match(r"^([A-Za-z]):[\\/](.*)$", raw)
    if m:
        drive = m.group(1).lower()
        rest = m.group(2).replace("\\", "/")
        return f"/mnt/{drive}/{rest}"
    return raw


def normalize_input_path(path: str | os.PathLike[str]) -> Path:
    """Resolve a user-entered data folder to an absolute path.

    - Rejects relative paths — the folder must be given as an absolute path so it
      never lands inside the project/working directory by accident.
    - When running under WSL, accepts Windows-style paths (``C:\\...``) and maps
      them onto the ``/mnt/<drive>`` mount so they point at the real Windows
      folder. Native ``/mnt/c/...`` and ``~/...`` inputs keep working.
    """
    raw = str(path).strip().strip('"')
    if not raw:
        raise ValueError("数据文件夹路径不能为空。")
    if _looks_like_windows_path(raw) and _running_on_wsl():
        raw = _windows_to_wsl(raw)
    p = Path(raw).expanduser()
    if not p.is_absolute():
        raise ValueError(
            "请输入绝对路径，例如 /home/you/mail-data、/mnt/c/Users/You/MailData，"
            "或（在 WSL 中）C:\\Users\\You\\MailData。"
        )
    return p.resolve()


def set_data_dir(path: str | os.PathLike[str]) -> Path:
    """Persist the chosen data folder, creating it and its ``settings.json``.

    Requires an absolute path (see :func:`normalize_input_path`) and validates it
    is usable (creatable + writable) before recording it, so a bad choice fails
    loudly at setup rather than at first DB write.
    """
    data_dir = normalize_input_path(path)
    data_dir.mkdir(parents=True, exist_ok=True)
    if not os.access(data_dir, os.W_OK):
        raise PermissionError(f"数据文件夹不可写：{data_dir}")

    pointer = _bootstrap_config_path()
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(
        json.dumps({"data_dir": str(data_dir)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Seed settings.json if absent (never clobber existing prefs).
    settings_file = data_dir / "settings.json"
    if not settings_file.exists():
        settings_file.write_text(
            json.dumps(_DEFAULT_SETTINGS, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return data_dir


def db_path() -> Path:
    data_dir = get_data_dir()
    if data_dir is None:
        raise RuntimeError("数据文件夹尚未配置，请先完成初始化设置。")
    return data_dir / "app.sqlite"


def _settings_path() -> Path:
    data_dir = get_data_dir()
    if data_dir is None:
        raise RuntimeError("数据文件夹尚未配置，请先完成初始化设置。")
    return data_dir / "settings.json"


def load_settings() -> dict[str, object]:
    try:
        raw = json.loads(_settings_path().read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raw = {}
    # Merge over defaults so new keys appear without a migration.
    return {**_DEFAULT_SETTINGS, **raw}


def save_settings(values: dict[str, object]) -> dict[str, object]:
    merged = {**load_settings(), **values}
    _settings_path().write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return merged


def ensure_data_dir() -> Path:
    """Return the configured data folder, creating it if missing.

    SQLite will not create missing parent directories, so callers must ensure the
    folder exists before opening the DB. Raises if the folder can't be created
    (e.g. an unmounted drive), which the startup path treats as "reset to setup".
    """
    data_dir = get_data_dir()
    if data_dir is None:
        raise RuntimeError("数据文件夹尚未配置，请先完成初始化设置。")
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def clear_data_dir() -> None:
    """Forget the recorded data folder (drop the bootstrap pointer) so the app
    returns to first-run setup. Used to recover from a stale/unusable path.
    No-op when the data dir is pinned via the env override."""
    if os.environ.get(_ENV_DATA_DIR):
        return
    try:
        _bootstrap_config_path().unlink()
    except FileNotFoundError:
        pass


def change_data_dir(path: str | os.PathLike[str]) -> Path:
    """Move the data folder to ``path`` and record it (Settings → change path).

    Copies the SQLite DB, settings, and encrypted secrets from the current folder
    to the new one (only files that don't already exist at the destination), so
    accounts/emails/keys survive the move instead of the app coming up empty.
    Then persists the pointer via :func:`set_data_dir`. Callers must reset the DB
    engine afterwards so it reopens against the new file.
    """
    old = get_data_dir()
    new = normalize_input_path(path)
    new.mkdir(parents=True, exist_ok=True)
    if not os.access(new, os.W_OK):
        raise PermissionError(f"数据文件夹不可写：{new}")

    if old is not None and old.exists() and old.resolve() != new.resolve():
        for name in _MIGRATE_FILES:
            src, dst = old / name, new / name
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)

    return set_data_dir(new)
