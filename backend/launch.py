"""Freeze-safe entry point for the packaged one-click binary.

Dev/server runs still use ``run.py`` (uvicorn import-string + optional reload).
This module is the entry PyInstaller bundles instead, because a frozen app can't
re-import ``app.main:app`` by string — it must be handed the app *object*.

It also makes the binary friendly for non-technical users: it defaults the
allowed CORS origin to the hosted frontend so the browser can reach this local
backend out of the box, prints a plain-language banner, opens the site, and turns
a "port already in use" error into a readable message instead of a traceback.
"""

from __future__ import annotations

import multiprocessing
import os
import sys
import webbrowser

# The hosted frontend that talks to this local backend. Kept in sync with the
# Dockerfile's MAIL_AGENT_CORS_ORIGINS default and the README.
HOSTED_APP_URL = "https://mail-agent.vercel.app"

# Allow the hosted site plus a local dev frontend by default. An explicit
# MAIL_AGENT_CORS_ORIGINS env still wins (setdefault only fills when unset).
_DEFAULT_ORIGINS = f"{HOSTED_APP_URL},http://localhost:5173,http://127.0.0.1:5173"

DEFAULT_PORT = 8765


def _banner(host: str, port: int) -> str:
    line = "─" * 58
    return (
        f"\n{line}\n"
        f"  Mail Agent — your local backend is running.\n\n"
        f"  1. Keep this window open (closing it stops the backend).\n"
        f"  2. Open the app in Chrome, Edge, or Firefox:\n"
        f"        {HOSTED_APP_URL}\n\n"
        f"  Listening on http://{host}:{port}  ·  your data stays on this PC.\n"
        f"{line}\n"
    )


def main() -> int:
    # Required before anything may spawn helper processes in a frozen build.
    multiprocessing.freeze_support()

    # Must be set BEFORE importing app.main, which reads the env at import time.
    os.environ.setdefault("MAIL_AGENT_CORS_ORIGINS", _DEFAULT_ORIGINS)

    host = os.environ.get("MAIL_AGENT_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("MAIL_AGENT_PORT", str(DEFAULT_PORT)))
    except ValueError:
        port = DEFAULT_PORT

    import uvicorn

    from app.main import app

    print(_banner(host, port), flush=True)

    # Best-effort: open the hosted app for the user. Never fail because of this.
    if os.environ.get("MAIL_AGENT_NO_BROWSER") != "1":
        try:
            webbrowser.open(HOSTED_APP_URL)
        except Exception:
            pass

    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except OSError as exc:
        # errno 48 (macOS) / 98 (Linux) / 10048 (Windows) = address already in use.
        if getattr(exc, "errno", None) in (48, 98, 10048):
            print(
                f"\n[!] Port {port} is already in use.\n"
                f"    Mail Agent may already be running in another window — if so,\n"
                f"    just open {HOSTED_APP_URL} in your browser.\n"
                f"    Otherwise close whatever is using port {port} and start again.\n",
                file=sys.stderr,
                flush=True,
            )
            return 1
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
