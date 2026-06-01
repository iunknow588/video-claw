"""
Preflight checks before real AI API integration testing.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.CEO.core.config import settings


def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}***{value[-4:]}"


def print_check(name: str, ok: bool, detail: str) -> None:
    status = "OK" if ok else "MISSING"
    print(f"[{status}] {name}: {detail}")


def main() -> int:
    print("== AI Video Pipeline Preflight Check ==")
    print_check("DATABASE_URL", bool(settings.DATABASE_URL), settings.DATABASE_URL)
    print_check("VIDEO_STORAGE_BACKEND", bool(settings.VIDEO_STORAGE_BACKEND), settings.VIDEO_STORAGE_BACKEND)
    print_check(
        "AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED",
        True,
        str(settings.AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED),
    )

    print_check("DEEPSEEK_API_KEY", bool(settings.DEEPSEEK_API_KEY), mask(settings.DEEPSEEK_API_KEY))
    print_check("DEEPSEEK_BASE_URL", bool(settings.DEEPSEEK_BASE_URL), settings.DEEPSEEK_BASE_URL)
    print_check("DEEPSEEK_MODEL", bool(settings.DEEPSEEK_MODEL), settings.DEEPSEEK_MODEL)

    print_check("GLM_API_KEY", bool(settings.GLM_API_KEY), mask(settings.GLM_API_KEY))
    print_check("GLM_BASE_URL", bool(settings.GLM_BASE_URL), settings.GLM_BASE_URL)
    print_check("GLM_MODEL", bool(settings.GLM_MODEL), settings.GLM_MODEL)

    print_check("SEEDANCE_API_KEY", bool(settings.SEEDANCE_API_KEY), mask(settings.SEEDANCE_API_KEY))
    print_check("SEEDANCE_BASE_URL", bool(settings.SEEDANCE_BASE_URL), settings.SEEDANCE_BASE_URL)
    print_check("SEEDANCE_MODEL", bool(settings.SEEDANCE_MODEL), settings.SEEDANCE_MODEL)

    backend = settings.VIDEO_STORAGE_BACKEND.lower()
    if backend == "local":
        print_check("MEDIA_ROOT", bool(settings.MEDIA_ROOT), settings.MEDIA_ROOT)
    elif backend == "s3_compatible":
        print_check("S3_BUCKET", bool(settings.S3_BUCKET), settings.S3_BUCKET)
        print_check("S3_ACCESS_KEY_ID", bool(settings.S3_ACCESS_KEY_ID), mask(settings.S3_ACCESS_KEY_ID))
        print_check("S3_SECRET_ACCESS_KEY", bool(settings.S3_SECRET_ACCESS_KEY), mask(settings.S3_SECRET_ACCESS_KEY))

    missing = [
        name
        for name, value in [
            ("DEEPSEEK_API_KEY", settings.DEEPSEEK_API_KEY),
            ("GLM_API_KEY", settings.GLM_API_KEY),
            ("SEEDANCE_API_KEY", settings.SEEDANCE_API_KEY),
        ]
        if not value
    ]

    if missing and not settings.AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED:
        print("\nReal API mode is enabled, but some keys are missing:")
        for item in missing:
            print(f"- {item}")
        return 1

    print("\nPreflight check finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
