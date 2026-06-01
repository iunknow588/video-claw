from fastapi import APIRouter

from departments.CEO.router.endpoints.cao.console import router as console_router
from departments.CEO.router.endpoints.cao.governance import router as governance_router
from departments.CEO.router.endpoints.cao.workflows import router as workflows_router

router = APIRouter()
router.include_router(console_router)
router.include_router(workflows_router)
router.include_router(governance_router)
