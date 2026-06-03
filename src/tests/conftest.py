import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import departments.CIO.models  # noqa: F401
from departments.CEO.core.config import settings
from departments.CIO.db.session import get_db
from departments.CIO.models.base import Base
from main import app


@pytest.fixture(autouse=True)
def isolate_external_ai_providers(monkeypatch):
    """
    Keep tests deterministic by disabling live provider credentials from .env.
    """
    monkeypatch.setattr(settings.ai_providers.runtime, "use_placeholder_when_unconfigured", True)
    monkeypatch.setattr(settings.ai_providers.xfyun_maas, "api_key", "")
    monkeypatch.setattr(settings.ai_providers.seedance, "api_key", "")
    monkeypatch.setattr(settings.ai_providers.hidream, "app_id", "")
    monkeypatch.setattr(settings.ai_providers.hidream, "api_key", "")
    monkeypatch.setattr(settings.ai_providers.hidream, "api_secret", "")


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as db:
        yield db
        await db.rollback()

    await engine.dispose()


@pytest_asyncio.fixture
async def api_client(session: AsyncSession):
    async def override_get_db():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()
