"""
Preflight checks before real AI API integration testing.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from departments.CEO.core.config import settings


def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}***{value[-4:]}"


def print_check(name: str, ok: bool, detail: str) -> None:
    status = "OK" if ok else "MISSING"
    print(f"[{status}] {name}: {detail}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run static preflight checks for AI provider wiring.")
    parser.add_argument(
        "--live-seedance",
        action="store_true",
        help="Perform a real create-task request against the configured Ark/Seedance video model.",
    )
    parser.add_argument(
        "--seedance-model",
        default=settings.SEEDANCE_MODEL,
        help="Override the Seedance model used by --live-seedance.",
    )
    return parser.parse_args()


def run_live_seedance_check(model: str) -> int:
    if not settings.SEEDANCE_API_KEY or not settings.SEEDANCE_BASE_URL or not model:
        print("\n[SKIP] Live Seedance check skipped because key/base_url/model is incomplete.")
        return 0

    url = f"{settings.SEEDANCE_BASE_URL.rstrip('/')}/contents/generations/tasks"
    payload = {
        "model": model,
        "content": [
            {
                "type": "text",
                "text": "测试一个 5 秒的竖屏短视频，清晨湖面，电影感 --resolution 720p --duration 5",
            }
        ],
        "duration": 5,
        "ratio": "9:16",
        "watermark": False,
        "generate_audio": False,
    }
    headers = {
        "Authorization": f"Bearer {settings.SEEDANCE_API_KEY}",
        "Content-Type": "application/json",
    }

    print("\n== Live Seedance Check ==")
    print(f"model={model}")
    response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
    print(f"http_status={response.status_code}")
    body = response.text.strip()
    if len(body) > 1200:
        body = f"{body[:1200]}..."
    print(body)
    return 0 if response.is_success else 1


def main() -> int:
    args = parse_args()
    print("== AI Video Pipeline Preflight Check ==")
    print_check("DATABASE_URL", bool(settings.DATABASE_URL), settings.DATABASE_URL)
    print_check("VIDEO_STORAGE_BACKEND", bool(settings.VIDEO_STORAGE_BACKEND), settings.VIDEO_STORAGE_BACKEND)
    print_check(
        "AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED",
        True,
        str(settings.AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED),
    )

    print_check("XFYUN_MAAS_API_KEY", bool(settings.XFYUN_MAAS_API_KEY), mask(settings.XFYUN_MAAS_API_KEY))
    print_check("XFYUN_MAAS_BASE_URL", bool(settings.XFYUN_MAAS_BASE_URL), settings.XFYUN_MAAS_BASE_URL)
    print_check("XFYUN_MAAS_MODEL", bool(settings.XFYUN_MAAS_MODEL), settings.XFYUN_MAAS_MODEL)
    print_check("XFYUN_MAAS_RESOURCE_ID", True, settings.XFYUN_MAAS_RESOURCE_ID)
    print_check("HIDREAM_APP_ID", bool(settings.HIDREAM_APP_ID), mask(settings.HIDREAM_APP_ID))
    print_check("HIDREAM_API_KEY", bool(settings.HIDREAM_API_KEY), mask(settings.HIDREAM_API_KEY))
    print_check("HIDREAM_API_SECRET", bool(settings.HIDREAM_API_SECRET), mask(settings.HIDREAM_API_SECRET))
    print_check("HIDREAM_CREATE_URL", bool(settings.HIDREAM_CREATE_URL), settings.HIDREAM_CREATE_URL)
    print_check("HIDREAM_QUERY_URL", bool(settings.HIDREAM_QUERY_URL), settings.HIDREAM_QUERY_URL)

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
            ("XFYUN_MAAS_API_KEY", settings.XFYUN_MAAS_API_KEY),
            ("SEEDANCE_API_KEY", settings.SEEDANCE_API_KEY),
        ]
        if not value
    ]

    if missing and not settings.AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED:
        print("\nReal API mode is enabled, but some keys are missing:")
        for item in missing:
            print(f"- {item}")
        return 1

    print("\nSuggested next checks:")
    print(r"- python src\scripts\check_seedance_access.py")
    print(r"- python src\scripts\api_workflow_smoke.py")

    if args.live_seedance:
        live_status = run_live_seedance_check(args.seedance_model)
        if live_status != 0:
            return live_status

    print("\nPreflight check finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
