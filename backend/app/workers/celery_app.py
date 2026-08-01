"""Celery app instance (architecture.md §4, §10)."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "company_chat",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks_files", "app.workers.tasks_notifications"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)
