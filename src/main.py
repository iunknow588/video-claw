"""AI Video Auto Production Line - Main Entry Point."""

import uvicorn

from app.CEO.app import app
from app.CEO.services.application_runtime import get_application_runtime


if __name__ == "__main__":
    application_runtime = get_application_runtime()
    uvicorn.run(
        "main:app",
        host=application_runtime.server.host,
        port=application_runtime.server.port,
        reload=application_runtime.debug,
        workers=application_runtime.server.resolved_workers(),
    )
