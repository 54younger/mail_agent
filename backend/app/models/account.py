"""Bound IMAP account. One row (single-user app), but modeled as a table so
rebinding is a simple delete+insert."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class Account(Base):
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    host: Mapped[str] = mapped_column(String, default="")
    port: Mapped[int] = mapped_column(Integer, default=993)
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    username: Mapped[str] = mapped_column(String, default="")

    # Key under which the password is stored in the secrets store (keyring/file).
    credential_key: Mapped[str] = mapped_column(String, default="")
    display_name: Mapped[str] = mapped_column(String, default="")

    # IMAP UIDVALIDITY — detects server-side folder resets.
    uid_validity: Mapped[int] = mapped_column(Integer, default=0)
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
