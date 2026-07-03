"""Async SQLAlchemy engine/session bound to the user's local SQLite file.

The data folder is chosen at runtime (first-run setup), so the engine is created
lazily and can be reset if the folder changes. Models declare against ``Base``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from . import config


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _sqlite_url() -> str:
    return f"sqlite+aiosqlite:///{config.db_path()}"


def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker
    if _engine is None:
        _engine = create_async_engine(_sqlite_url(), future=True)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def reset_engine() -> None:
    """Dispose the engine (e.g. after the data folder changes) so the next call
    rebuilds it against the new SQLite file."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


async def init_db() -> None:
    """Create tables for all registered models. Importing ``models`` registers
    them on ``Base.metadata`` as a side effect."""
    from . import models  # noqa: F401  (registers mappers)

    # SQLite won't create missing parent dirs — ensure the data folder exists.
    config.ensure_data_dir()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_schema)


def _migrate_schema(conn) -> None:
    """Tiny migrations for SQLite (no Alembic yet) so pre-existing DBs keep
    working after schema changes."""
    from sqlalchemy import inspect, text

    insp = inspect(conn)
    table_names = set(insp.get_table_names())

    # Add the job-title column to pre-existing job boards (dedup unit is
    # company + position). Independent of the email_message migrations below.
    if "job_application" in table_names:
        job_cols = {c["name"] for c in insp.get_columns("job_application")}
        if "position" not in job_cols:
            conn.execute(
                text("ALTER TABLE job_application ADD COLUMN position TEXT DEFAULT ''")
            )

    if "email_message" not in table_names:
        return

    cols = {c["name"] for c in insp.get_columns("email_message")}
    if "account_id" not in cols:
        conn.execute(
            text("ALTER TABLE email_message ADD COLUMN account_id INTEGER DEFAULT 0")
        )

    # If the table still carries the old UNIQUE(folder, uid) constraint (i.e. it
    # lacks the multi-account UNIQUE(account_id, folder, uid)), rebuild it — SQLite
    # can't alter a constraint in place. Legacy rows (account_id 0) are remapped to
    # the sole account so multi-account inserts neither collide nor duplicate.
    uniques = insp.get_unique_constraints("email_message")
    has_new = any(set(u["column_names"]) == {"account_id", "folder", "uid"} for u in uniques)
    if not has_new:
        _rebuild_email_message(conn)

    # Add the job-pipeline screen column to pre-existing DBs (re-inspect: the
    # table may have just been rebuilt above, in which case it already exists).
    cols_now = {c["name"] for c in inspect(conn).get_columns("email_message")}
    if "job_screened" not in cols_now:
        conn.execute(
            text("ALTER TABLE email_message ADD COLUMN job_screened INTEGER DEFAULT 0")
        )


def _rebuild_email_message(conn) -> None:
    from sqlalchemy import text

    from .models import EmailMessage

    accounts = conn.execute(text("SELECT id FROM account")).fetchall()
    target = accounts[0][0] if len(accounts) == 1 else 0

    conn.execute(text("ALTER TABLE email_message RENAME TO email_message_old"))
    EmailMessage.__table__.create(conn, checkfirst=False)
    # COALESCE the NOT NULL columns so legacy rows with NULLs aren't silently
    # dropped by OR IGNORE (which then only skips genuine unique-key duplicates).
    conn.execute(
        text(
            """
            INSERT OR IGNORE INTO email_message
                (id, account_id, uid, folder, from_address, to_addresses,
                 subject, body_text, date, translated_text, detected_lang)
            SELECT id,
                   CASE WHEN COALESCE(account_id, 0) = 0 THEN :target ELSE account_id END,
                   COALESCE(uid, ''),
                   COALESCE(folder, 'INBOX'),
                   COALESCE(from_address, ''),
                   COALESCE(to_addresses, ''),
                   COALESCE(subject, ''),
                   COALESCE(body_text, ''),
                   COALESCE(date, CURRENT_TIMESTAMP),
                   translated_text, detected_lang
            FROM email_message_old
            """
        ),
        {"target": target},
    )
    conn.execute(text("DROP TABLE email_message_old"))


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session, committing on success and rolling
    back on error."""
    maker = get_sessionmaker()
    async with maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
