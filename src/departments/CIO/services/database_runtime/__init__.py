from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import make_url

from departments.CEO.core.config import settings
from departments.CIO.services.runtime_assets import resolve_project_path


@dataclass(slots=True)
class DatabaseRuntime:
    url: str
    pool_size: int
    max_overflow: int
    pool_timeout: int
    echo: bool
    version: int


def normalize_database_url(url: str) -> str:
    database_url = make_url(url)
    if not database_url.drivername.startswith("sqlite"):
        return url

    database_path = database_url.database or ""
    if not database_path or database_path == ":memory:":
        return url

    path_obj = Path(database_path)
    if path_obj.is_absolute() or database_path.startswith("/"):
        return url

    resolved = resolve_project_path(database_path).as_posix()
    return database_url.set(database=resolved).render_as_string(hide_password=False)


def get_database_runtime() -> DatabaseRuntime:
    database = settings.database
    return DatabaseRuntime(
        url=normalize_database_url(str(database.url)),
        pool_size=int(database.pool_size),
        max_overflow=int(database.max_overflow),
        pool_timeout=int(database.pool_timeout),
        echo=bool(database.echo),
        version=int(settings.version("cio_database")),
    )
