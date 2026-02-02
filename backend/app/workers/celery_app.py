from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "consensus",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.pipeline"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
)
