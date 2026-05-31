"""
AI Video Auto Production Line - Main Entry Point
MVP Version - FastAPI Application
"""

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.db.session import init_db


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    setup_logging()
    
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-powered video content production system",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )
    
    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    application.include_router(api_router, prefix="/api/v1")

    media_root = Path(settings.MEDIA_ROOT)
    media_root.mkdir(parents=True, exist_ok=True)
    application.mount(
        settings.MEDIA_URL_PREFIX,
        StaticFiles(directory=media_root),
        name="media",
    )

    cao_console_path = Path(__file__).resolve().parent / "app" / "CAO" / "console" / "index.html"

    @application.get("/cao", include_in_schema=False)
    async def cao_console():
        return FileResponse(cao_console_path)

    @application.get("/ceo", include_in_schema=False)
    async def cao_console_compat_alias():
        return FileResponse(cao_console_path)
    
    @application.on_event("startup")
    async def startup_event():
        """Application startup handler"""
        await init_db()
    
    @application.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "version": settings.APP_VERSION}
    
    return application


app = create_application()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.SERVER_WORKERS,
    )
