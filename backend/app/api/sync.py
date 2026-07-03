"""Trigger a sync and poll its progress."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..schemas.sync import SyncStatus
from ..services import sync_manager

router = APIRouter(prefix="/api/sync", tags=["sync"])


def _to_status(s: sync_manager.SyncState) -> SyncStatus:
    return SyncStatus(
        running=s.running,
        fetched=s.fetched,
        total=s.total,
        done=s.done,
        error=s.error,
        hint=s.hint,
        kind=s.kind,
        detail=s.detail,
    )


@router.post("", response_model=SyncStatus)
async def trigger_sync(full: bool = Query(False)) -> SyncStatus:
    await sync_manager.start_sync(full=full)
    return _to_status(sync_manager.get_state())


@router.get("/status", response_model=SyncStatus)
async def sync_status() -> SyncStatus:
    return _to_status(sync_manager.get_state())
