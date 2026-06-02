"""
Smoke test for the first three content stages only:
hotspot -> analysis DNA report -> original script.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx


BASE_URL = os.environ.get("LOBSTER_BASE_URL", "http://127.0.0.1:8000")
PLATFORM = os.environ.get("LOBSTER_PLATFORM", "douyin")
KEYWORD = os.environ.get("LOBSTER_KEYWORD", "lobster")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")


def request_json(method: str, path: str, **kwargs: Any) -> Any:
    response = httpx.request(
        method,
        f"{BASE_URL}{path}",
        timeout=180.0,
        trust_env=False,
        **kwargs,
    )
    response.raise_for_status()
    return response.json()


def pretty_print(label: str, payload: Any) -> None:
    print(f"\n== {label} ==")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    print("== Front Flow Smoke Test ==")
    print(f"Base URL: {BASE_URL}")
    print(f"Platform: {PLATFORM}")
    print(f"Keyword: {KEYWORD}")

    health = request_json("GET", "/health")
    print(f"[health] {health}")

    hotspots = request_json(
        "POST",
        "/api/hotspots/fetch",
        json={"platform": PLATFORM, "keyword": KEYWORD, "count": 1},
    )
    hotspot = hotspots[0]
    pretty_print("Hotspot", hotspot)

    analysis = request_json(
        "POST",
        "/api/analysis",
        json={"hotspot_id": hotspot["uuid"], "analysis_type": "comprehensive"},
    )
    pretty_print("DNA Report", analysis)

    script = request_json(
        "POST",
        "/api/scripts",
        json={
            "analysis_id": analysis["uuid"],
            "content_type": "knowledge",
            "style": "clean",
            "topic": "Front flow smoke test",
            "duration": 30,
        },
    )
    pretty_print("Script", script)

    print("\nFront flow smoke test finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
