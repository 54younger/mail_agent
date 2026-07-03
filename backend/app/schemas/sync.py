from __future__ import annotations

from pydantic import BaseModel


class SyncStatus(BaseModel):
    running: bool
    fetched: int
    total: int
    done: bool
    error: str | None = None
    hint: str | None = None
    kind: str | None = None
    detail: str | None = None
