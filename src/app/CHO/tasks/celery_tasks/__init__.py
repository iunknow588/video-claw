"""
Celery Task Definitions
"""

from celery import Celery

from app.CEO.core.logging import get_logger
from app.CIO.services.redis_runtime import get_redis_runtime

logger = get_logger(__name__)
redis_runtime = get_redis_runtime()

celery_app = Celery(
    "ai_video_tasks",
    broker=redis_runtime.build_url(),
    backend=redis_runtime.build_url(),
)


@celery_app.task(bind=True, max_retries=3)
def process_video_generation(self, task_id: str):
    """Process video generation task."""
    logger.info("Processing video task", task_id=task_id)
    return {"status": "completed", "task_id": task_id}


@celery_app.task
def fetch_hotspots_daily():
    """Daily hotspot fetching task."""
    logger.info("Running daily hotspot fetch")
    return {"status": "completed"}


@celery_app.task
def cleanup_old_tasks():
    """Cleanup old completed tasks."""
    logger.info("Running task cleanup")
    return {"status": "completed"}
