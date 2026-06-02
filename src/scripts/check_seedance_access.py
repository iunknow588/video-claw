"""
Direct connectivity smoke test for the configured Seedance/Ark video model.
"""

from __future__ import annotations

import argparse
import json
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Ark/Seedance video model access.")
    parser.add_argument(
        "--model",
        default=settings.SEEDANCE_MODEL,
        help="Override the model name from .env",
    )
    parser.add_argument(
        "--prompt",
        default="测试一个 5 秒的竖屏短视频，清晨湖面，电影感 --resolution 720p --duration 5",
        help="Prompt used for the create-task smoke test",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = settings.SEEDANCE_BASE_URL.rstrip("/")
    api_key = settings.SEEDANCE_API_KEY

    print("== Seedance Access Check ==")
    print(f"BASE_URL={base_url}")
    print(f"MODEL={args.model}")
    print(f"API_KEY={mask(api_key)}")

    if not api_key:
        print("\n[ERROR] SEEDANCE_API_KEY is not configured.")
        return 1
    if not base_url:
        print("\n[ERROR] SEEDANCE_BASE_URL is not configured.")
        return 1
    if not args.model:
        print("\n[ERROR] No model provided.")
        return 1

    url = f"{base_url}/contents/generations/tasks"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": args.model,
        "content": [
            {
                "type": "text",
                "text": args.prompt,
            }
        ],
        "duration": 5,
        "ratio": "9:16",
        "watermark": False,
        "generate_audio": False,
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
    except Exception as exc:  # noqa: BLE001
        print(f"\n[ERROR] Request failed before receiving a response: {exc}")
        return 1

    print(f"\nHTTP_STATUS={response.status_code}")
    body_text = response.text.strip()
    if len(body_text) > 1500:
        body_text = f"{body_text[:1500]}..."
    print("RESPONSE_BODY=")
    print(body_text)

    if response.is_success:
        try:
            data = response.json()
        except json.JSONDecodeError:
            print("\n[WARN] Request succeeded but the response is not valid JSON.")
            return 0
        task_id = (
            data.get("id")
            or data.get("task_id")
            or ((data.get("data") or {}).get("id"))
            or ((data.get("data") or {}).get("task_id"))
        )
        print(f"\n[OK] Create task request accepted. task_id={task_id}")
        return 0

    print("\n[FAIL] The configured model/key is not currently usable.")
    print("Please verify the exact model name and whether the current Ark account has access.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
