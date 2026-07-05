"""First-run data-folder selection."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from .. import config, db
from ..schemas.setup import DataFolderIn, DataFolderOut

router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.post("/data-folder", response_model=DataFolderOut)
async def set_data_folder(payload: DataFolderIn) -> DataFolderOut:
    try:
        data_dir = await run_in_threadpool(config.set_data_dir, payload.path)
    except ValueError as e:
        # Relative/empty path — message is already user-friendly.
        raise HTTPException(status_code=400, detail=str(e)) from e
    except (PermissionError, OSError) as e:
        raise HTTPException(status_code=400, detail=f"Cannot use this folder: {e}") from e

    # Point the engine at the (possibly new) SQLite file and create tables.
    await db.reset_engine()
    await db.init_db()
    return DataFolderOut(data_dir=str(data_dir))
