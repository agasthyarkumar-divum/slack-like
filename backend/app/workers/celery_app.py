"""Celery app instance (architecture.md §4, §10).

Task modules (tasks_files.py for encrypt/compress/thumbnail, tasks_notifications.py
for FCM push/digests) land in Phase 7 and Phase 9 and get added to `include` below.
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "company_chat",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)
