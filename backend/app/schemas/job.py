from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TimelineEntry(BaseModel):
    status: int
    ts: str


class JobApplicationOut(BaseModel):
    id: int
    company: str
    applied_at: datetime
    status_code: int
    email_id: int
    manually_edited: bool
    timeline: list[TimelineEntry]
    # Subject of the source email (for the card), when available.
    source_subject: str | None = None


class JobStatusUpdate(BaseModel):
    status_code: int = Field(ge=0, le=99)


class ManualJobIn(BaseModel):
    company: str = Field(min_length=1)
    applied_at: datetime | None = None
    status_code: int = Field(default=0, ge=0, le=99)


class JobEdit(BaseModel):
    company: str | None = None
    applied_at: datetime | None = None
    status_code: int | None = Field(default=None, ge=0, le=99)


class ExtractResult(BaseModel):
    created: int
    scanned: int
