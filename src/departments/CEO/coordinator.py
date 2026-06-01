from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from departments.CEO.router import api_router
from departments.CEO.services.application_runtime import get_application_runtime
from departments.CIO.services.storage import get_storage_runtime


def register_ceo_routes(application: FastAPI) -> None:
    """Register CEO-managed public and internal routes.

    This centralizes all route registration that belongs to CEO (governance
    and orchestration). External components MUST NOT directly mount or
    manipulate these routes.
    """
    # public API mount
    application.include_router(api_router, prefix="/api")

    # Tag-based internal route hiding: routes that belong to governance/control
    # can be marked by tags (e.g. 'control', 'orchestration', 'operations')
    # and will be removed from the generated OpenAPI schema to keep CEO
    # hidden from external documentation. Update this list as needed.
    INTERNAL_TAGS = {"control", "orchestration", "operations"}

    for route in list(application.routes):
        tags = getattr(route, "tags", None) or []
        if any(tag in INTERNAL_TAGS for tag in tags):
            try:
                route.include_in_schema = False
            except Exception:
                # best-effort: some route objects may be immutable in certain
                # frameworks or versions; ignore if we can't change them.
                pass

    # media static mount
    storage_runtime = get_storage_runtime()
    media_root = storage_runtime.media_root_path
    media_root.mkdir(parents=True, exist_ok=True)
    application.mount(
        storage_runtime.media_url_prefix,
        StaticFiles(directory=media_root),
        name="media",
    )

    # CAO console (served by CEO coordinator as a public convenience)
    cao_console_path = Path(__file__).resolve().parents[1] / "CAO" / "console" / "index.html"
    try:
        cao_console_html = cao_console_path.read_text(encoding="utf-8")
    except Exception:
        cao_console_html = "<html><body><h1>CAO console not found</h1></body></html>"

    @application.get("/cao", include_in_schema=False)
    async def cao_console():
        return HTMLResponse(cao_console_html)

    # health
    @application.get("/health")
    async def health_check():
        application_runtime = get_application_runtime()
        return {"status": "healthy", "version": application_runtime.version}
