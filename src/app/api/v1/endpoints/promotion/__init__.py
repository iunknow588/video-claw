"""Compatibility promotion endpoint alias for the canonical CMO API."""

from app.api.v1.endpoints.cmo import router

__all__ = ["router"]
