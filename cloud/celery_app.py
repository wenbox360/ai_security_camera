from celery import Celery
from .config import settings

_task_package = f"{__package__}.tasks"

# Create Celery app
celery_app = Celery(
    "security_camera",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        f"{_task_package}.llm_analysis",
        f"{_task_package}.file_cleanup",
        f"{_task_package}.notifications",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
