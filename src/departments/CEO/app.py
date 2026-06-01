from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from departments.CEO.router import api_router
from departments.CEO.core.logging import setup_logging
from departments.CEO.services.application_runtime import get_application_runtime
from departments.CIO.db.session import ensure_database_ready
from departments.CIO.services.storage import get_storage_runtime


@asynccontextmanager
async def application_lifespan(_: FastAPI):
    await ensure_database_ready()
    yield


def create_application() -> FastAPI:
    """Create and configure the canonical application entry."""
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

    # NOTE: Route registration (public APIs, media mount, console, health)
    # is delegated to `departments.CEO.coordinator.register_ceo_routes` so that
    # CEO can centrally control which routes are public vs internal.

    return application


app = create_application()


if __name__ == "__main__":
    application_runtime = get_application_runtime()
    uvicorn.run(
        "departments.CEO.app:app",
        host=application_runtime.server.host,
        port=application_runtime.server.port,
        reload=application_runtime.debug,
        workers=application_runtime.server.resolved_workers(),
    )

