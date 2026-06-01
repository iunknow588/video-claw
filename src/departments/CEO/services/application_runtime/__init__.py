from __future__ import annotations

from dataclasses import dataclass

from departments.CEO.core.config import settings


@dataclass(slots=True)
class ServerRuntime:
    host: str
    port: int
    workers: int
    debug: bool

    def resolved_workers(self) -> int:
        return 1 if self.debug else self.workers


@dataclass(slots=True)
class LoggingRuntime:
    level: str
    format: str
    file: str
    max_bytes: int
    backup_count: int


@dataclass(slots=True)
class ApplicationRuntime:
    name: str
    version: str
    debug: bool
    env: str
    server: ServerRuntime
    logging: LoggingRuntime


def get_application_runtime() -> ApplicationRuntime:
    application = settings.application
    return ApplicationRuntime(
        name=str(application.app.name),
        version=str(application.app.version),
        debug=bool(application.app.debug),
        env=str(application.app.env),
        server=ServerRuntime(
            host=str(application.server.host),
            port=int(application.server.port),
            workers=int(application.server.workers),
            debug=bool(application.app.debug),
        ),
        logging=LoggingRuntime(
            level=str(application.logging.level),
            format=str(application.logging.format),
            file=str(application.logging.file),
            max_bytes=int(application.logging.max_bytes),
            backup_count=int(application.logging.backup_count),
        ),
    )
