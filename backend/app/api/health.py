"""Health + first-run status endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from .. import config

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health() -> dict[str, object]:
    data_dir = config.get_data_dir()
    return {
        "status": "ok",
        "configured": data_dir is not None,
        "data_dir": str(data_dir) if data_dir else None,
    }
