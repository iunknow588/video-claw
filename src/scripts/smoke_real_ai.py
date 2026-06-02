"""
Smoke test for real AI provider wiring.

This script calls the service layer directly so the user can verify
DeepSeek / GLM / Seedance credentials before full API workflow testing.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import departments.CIO.models  # noqa: F401
from departments.CEO.core.config import settings
from departments.CIO.models.base import Base
from departments.CIO.models.hotspot import HotspotItem
from departments.CCO.services.content_creation import AIAnalysisService
from departments.COO.services.script_management import ScriptService
from departments.COO.services.video_production import VideoService


async def main() -> int:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        hotspot = HotspotItem(
            platform="manual",
            content_id="smoke-001",
            title="Lobster smoke test topic",
            author="codex",
            category="knowledge",
            view_count=1000,
            like_count=100,
            comment_count=10,
        )
        session.add(hotspot)
        await session.flush()

        analysis = await AIAnalysisService(session).analyze_content(hotspot)
        print(f"[analysis] framework_summary={analysis.framework_summary!r}")

        script = await ScriptService(session).generate_script(
            analysis=analysis,
            content_type="knowledge",
            style="clean",
            topic="Smoke Test",
            duration=30,
        )
        print(f"[script] title={script.title!r} similarity={script.similarity_score}")

        script.status = "approved"
        task = await VideoService(session).create_task(script=script, style="realistic")
        task = await VideoService(session).process_task(task.uuid)
        print(f"[video] status={task.status!r} video_url={task.video_url!r}")

        await session.rollback()

    await engine.dispose()
    print("\nSmoke test finished.")
    print(f"AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED={settings.AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
