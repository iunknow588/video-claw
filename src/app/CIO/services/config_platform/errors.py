from __future__ import annotations


class ConfigPlatformError(RuntimeError):
    """Base error for centralized configuration management."""


class ConfigDomainNotFoundError(ConfigPlatformError):
    """Raised when a named configuration domain cannot be discovered."""


class ConfigValidationError(ConfigPlatformError):
    """Raised when configuration validation fails."""

    def __init__(self, domain: str, errors: list[dict[str, object]]) -> None:
        self.domain = domain
        self.errors = errors
        super().__init__(f"Configuration domain '{domain}' is invalid")
