from __future__ import annotations

from dataclasses import dataclass

from app.CEO.core.config import settings


@dataclass(slots=True)
class DatabaseRuntime:
    url: str
    pool_size: int
    max_overflow: int
    pool_timeout: int
    echo: bool
    version: int


def get_database_runtime() -> DatabaseRuntime:
    database = settings.database
    return DatabaseRuntime(
        url=str(database.url),
        pool_size=int(database.pool_size),
        max_overflow=int(database.max_overflow),
        pool_timeout=int(database.pool_timeout),
        echo=bool(database.echo),
        version=int(settings.version("cio_database")),
    )
