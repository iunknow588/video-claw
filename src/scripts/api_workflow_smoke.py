"""
Smoke test against a running local API server.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

import httpx


BASE_URL = os.environ.get("LOBSTER_BASE_URL", "http://127.0.0.1:8000")


def request_json(method: str, path: str, **kwargs: Any) -> Any:
    url = f"{BASE_URL}{path}"
    response = httpx.request(method, url, timeout=60.0, trust_env=False, **kwargs)
    response.raise_for_status()
    return response.json()


def main() -> int:
    print("== Live API Workflow Smoke Test ==")
    print(f"Base URL: {BASE_URL}")

    health = request_json("GET", "/health")
    print(f"[health] {health}")

    hotspots = request_json(
        "POST",
        "/api/hotspots/fetch",
        json={"platform": "douyin", "keyword": "lobster", "count": 1},
    )
    hotspot_id = hotspots[0]["uuid"]
    print(f"[hotspot] id={hotspot_id}")

    analysis = request_json(
        "POST",
        "/api/analysis",
        json={"hotspot_id": hotspot_id, "analysis_type": "comprehensive"},
    )
    analysis_id = analysis["uuid"]
    print(f"[analysis] id={analysis_id}")

    script = request_json(
        "POST",
        "/api/scripts",
        json={
            "analysis_id": analysis_id,
            "content_type": "knowledge",
            "style": "clean",
            "topic": "Lobster live smoke test",
            "duration": 30,
        },
    )
    script_id = script["uuid"]
    print(f"[script] id={script_id}")

    approved_script = request_json(
        "POST",
        f"/api/scripts/review/{script_id}",
        json={"approved": True, "feedback": "live smoke ok"},
    )
    print(f"[script review] status={approved_script['status']}")

    video_task = request_json(
        "POST",
        "/api/videos",
        json={"script_id": script_id, "style": "realistic", "size": "1080x1920"},
    )
    task_id = video_task["uuid"]
    print(f"[video task] id={task_id}")

    task_status = None
    for _ in range(10):
        time.sleep(1)
        task_status = request_json("GET", f"/api/videos/task/{task_id}")
        print(f"[video poll] status={task_status['status']}")
        if task_status["status"] in {"completed", "approved", "rejected", "failed"}:
            break

    storage = request_json("GET", "/api/operations/storage")
    print(f"[storage] backend={storage['backend']} configured={storage['configured']}")

    summary = request_json("GET", "/api/operations/summary")
    print(f"[summary] counts={summary['counts']}")

    print("\nLive API workflow smoke test finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

