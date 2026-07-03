"""Local launcher — binds to 127.0.0.1 only (single-user, self-hosted).

Usage:
    python run.py            # http://127.0.0.1:8765
    MAIL_AGENT_DATA_DIR=./data python run.py
"""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    host = os.environ.get("MAIL_AGENT_HOST", "127.0.0.1")
    port = int(os.environ.get("MAIL_AGENT_PORT", "8765"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
