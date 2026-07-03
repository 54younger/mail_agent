from __future__ import annotations

from pydantic import BaseModel, Field


class DataFolderIn(BaseModel):
    path: str = Field(min_length=1, description="Absolute or ~-relative folder path")


class DataFolderOut(BaseModel):
    data_dir: str
