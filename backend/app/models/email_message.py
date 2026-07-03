"""A synced email. Headers arrive first (list view); body is fetched lazily on
open. Translation results are cached here to avoid repeat Claude calls.

Note vs the old Flutter model: the embedding/embeddingModelId/categoryId fields
are gone (semantic search + classification were dropped); translated_text +
detected_lang are new (Phase 2)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class EmailMessage(Base):
    __tablename__ = "email_message"
    __table_args__ = (
        UniqueConstraint("account_id", "folder", "uid", name="uq_email_account_folder_uid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Owning account (FK to account.id). 0 for pre-multi-account legacy rows.
    account_id: Mapped[int] = mapped_column(Integer, index=True, default=0)

    # IMAP UID, scoped to a folder (stored as text to match provider formats).
    uid: Mapped[str] = mapped_column(String, index=True, default="")
    folder: Mapped[str] = mapped_column(String, default="INBOX")

    from_address: Mapped[str] = mapped_column(String, default="")
    to_addresses: Mapped[str] = mapped_column(String, default="")  # comma-separated
    subject: Mapped[str] = mapped_column(String, default="")

    # Empty until the message is opened; then holds HTML (preferred) or plain text.
    body_text: Mapped[str] = mapped_column(Text, default="")

    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    # Translation cache (Phase 2).
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_lang: Mapped[str | None] = mapped_column(String, nullable=True)

    # Job-pipeline screen state: 0=unscreened, 1=screened-not-job, 2=linked to a
    # JobApplication. Lets extraction skip already-judged mail instead of
    # re-sending the newest emails to the LLM on every run. server_default keeps
    # the column populated when the table is rebuilt (omitted-column inserts) and
    # when it's added to a pre-existing DB.
    job_screened: Mapped[int] = mapped_column(
        Integer, index=True, default=0, server_default="0"
    )
