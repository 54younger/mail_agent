from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TimelineEntry(BaseModel):
    status: int
    ts: str


class JobApplicationOut(BaseModel):
    id: int
    company: str
    position: str = ""
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
    position: str = ""
    applied_at: datetime | None = None
    status_code: int = Field(default=0, ge=0, le=99)


class JobEdit(BaseModel):
    company: str | None = None
    position: str | None = None
    applied_at: datetime | None = None
    status_code: int | None = Field(default=None, ge=0, le=99)


class ExtractStatus(BaseModel):
    running: bool
    phase: str  # "" | "cache" | "scan"
    total: int
    current: int
    stage: str  # "" | "keyword" | "classify" | "extract"
    created: int
    done: bool
    error: str | None = None
    hint: str | None = None
    detail: str | None = None


# ── Board summary (one row per company+position) and dashboard stats ──────────


class SummaryRecord(BaseModel):
    """One underlying JobApplication row inside a company+position group."""

    id: int
    email_id: int
    source_subject: str | None = None
    status_code: int
    applied_at: datetime
    timeline: list[TimelineEntry]


class ApplicationSummary(BaseModel):
    """A deduped application: all emails for one (company, position) merged."""

    company: str
    position: str
    applied_at: datetime  # earliest across the group
    status_code: int  # status of the most recent timeline event
    last_update: datetime  # newest timeline event across the group
    count: int  # number of underlying records
    manually_edited: bool
    primary_id: int  # record holding the latest event (target of status edits)
    records: list[SummaryRecord]


class TrendPoint(BaseModel):
    date: str  # YYYY-MM-DD
    count: int


class FunnelStage(BaseModel):
    status_code: int
    count: int


class JobStats(BaseModel):
    total: int  # number of application units (company+position)
    by_status: dict[int, int]  # status_code -> unit count
    trend: list[TrendPoint]  # applications per day (by applied_at)
    funnel: list[FunnelStage]  # reached-stage counts (applied/test/interview/offer)
    interview_rate: float  # reached-interview / total
    offer_rate: float  # reached-offer / total
