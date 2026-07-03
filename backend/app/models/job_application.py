"""A job application extracted from email (Phase 3). Status is stored as an int
code (parity with the Flutter JobStatus enum); the timeline is JSON text."""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class JobStatus(IntEnum):
    APPLIED = 0
    ONLINE_TEST = 1
    INTERVIEW = 2
    OFFER = 3
    REJECTED = 4
    UNKNOWN = 99

    @classmethod
    def from_code(cls, code: int) -> "JobStatus":
        try:
            return cls(code)
        except ValueError:
            return cls.UNKNOWN


class JobApplication(Base):
    __tablename__ = "job_application"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company: Mapped[str] = mapped_column(String, default="")
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status_code: Mapped[int] = mapped_column(Integer, default=JobStatus.APPLIED.value)

    # FK to EmailMessage.id that triggered this record (0 = manual entry).
    email_id: Mapped[int] = mapped_column(Integer, default=0, index=True)

    # True once the user overrides AI-extracted data — extraction won't clobber it.
    manually_edited: Mapped[bool] = mapped_column(Boolean, default=False)

    # JSON list of {"status": int, "ts": ISO8601} for the status timeline.
    timeline_json: Mapped[str] = mapped_column(Text, default="[]")
