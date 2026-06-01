"""
Project runtime asset path helpers.
"""

from __future__ import annotations

from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[5]


def get_runtime_root() -> Path:
    return get_project_root() / "runtime"


def resolve_project_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return get_project_root() / path
