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
