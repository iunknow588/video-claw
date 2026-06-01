"""
Database Session Management
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from departments.CEO.core.logging import get_logger
from departments.CIO.services.database_runtime import get_database_runtime

logger = get_logger(__name__)


class DatabaseSessionRuntime:
    """Lazy database dependency that rebuilds itself when config version changes."""

    def __init__(self) -> None:
        self._engine = None
        self._session_factory = None
        self._loaded_version: int | None = None

    def engine(self):
        self._ensure_current()
        return self._engine

    def session_factory(self):
        self._ensure_current()
        return self._session_factory

    def _ensure_current(self) -> None:
        database_runtime = get_database_runtime()
        current_version = database_runtime.version
        if self._engine is not None and self._session_factory is not None and self._loaded_version == current_version:
            return

        database_url = make_url(database_runtime.url)
        engine_kwargs = {"echo": database_runtime.echo}
        if not database_url.drivername.startswith("sqlite"):
            engine_kwargs.update(
                pool_size=database_runtime.pool_size,
                max_overflow=database_runtime.max_overflow,
                pool_timeout=database_runtime.pool_timeout,
            )

        self._engine = create_async_engine(database_runtime.url, **engine_kwargs)
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        self._loaded_version = current_version


database_runtime = DatabaseSessionRuntime()


async def get_db():
    """Dependency for FastAPI to get DB session."""
    async with database_runtime.session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def ensure_database_ready():
    """Verify database connectivity before serving traffic.

    Schema changes are managed through Alembic migrations.
    """

    async with database_runtime.engine().begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection verified; run Alembic migrations separately")
