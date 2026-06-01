"""
Logging Configuration
Structured logging with JSON format for production
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

import structlog

from app.CEO.services.application_runtime import get_application_runtime
from app.CIO.services.runtime_assets import resolve_project_path


def setup_logging() -> None:
    """Configure structured logging"""
    application_runtime = get_application_runtime()
    logging_runtime = application_runtime.logging

    # Always resolve runtime logs against the project root.
    log_path = resolve_project_path(logging_runtime.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    handlers.append(
        RotatingFileHandler(
            filename=log_path,
            maxBytes=logging_runtime.max_bytes,
            backupCount=logging_runtime.backup_count,
            encoding="utf-8",
        )
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, logging_runtime.level.upper()),
        handlers=handlers,
        force=True,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
            if logging_runtime.format == "json"
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """Get structured logger instance"""
    return structlog.get_logger(name)
