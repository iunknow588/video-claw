from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.router import api_router
from departments.CEO.core.logging import setup_logging
from departments.CEO.services.application_runtime import get_application_runtime
from departments.CIO.db.session import ensure_database_ready
from departments.CIO.services.storage import get_storage_runtime


@asynccontextmanager
async def application_lifespan(_: FastAPI):
    await ensure_database_ready()
    yield


def create_application() -> FastAPI:
    """Create and configure the neutral application shell."""
    setup_logging()
    application_runtime = get_application_runtime()

    application = FastAPI(
        title=application_runtime.name,
        version=application_runtime.version,
        description="AI-powered video content production system",
        docs_url="/docs" if application_runtime.debug else None,
        redoc_url="/redoc" if application_runtime.debug else None,
        lifespan=application_lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix="/api")

    internal_tags = {"control", "orchestration", "operations"}
    for route in list(application.routes):
        tags = getattr(route, "tags", None) or []
        if any(tag in internal_tags for tag in tags):
            route.include_in_schema = False

    storage_runtime = get_storage_runtime()
    media_root = storage_runtime.media_root_path
    media_root.mkdir(parents=True, exist_ok=True)
    application.mount(
        storage_runtime.media_url_prefix,
        StaticFiles(directory=media_root),
        name="media",
    )

    cao_console_path = Path(__file__).resolve().parents[1] / "departments" / "CAO" / "console" / "index.html"
    cao_console_html = cao_console_path.read_text(encoding="utf-8")

    @application.get("/cao", include_in_schema=False)
    async def cao_console():
        return HTMLResponse(cao_console_html)

    @application.get("/", include_in_schema=False)
    async def root_entry():
        return RedirectResponse(url="/cao", status_code=307)

    @application.get("/health")
    async def health_check():
        return {"status": "healthy", "version": application_runtime.version}

    return application


app = create_application()
