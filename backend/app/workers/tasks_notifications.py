"""FCM push (architecture.md §9). Stubbed the same way storage/s3_ready.py is:
the interface/call site exists and is wired up end-to-end, but there's no real
Firebase project to send to, so it logs instead of calling firebase-admin
(architecture.md §10) — swap the body for a real `firebase_admin.messaging.send()`
call once FCM credentials exist, no call-site changes needed elsewhere.
"""

import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="notifications.send_fcm_push")
def send_fcm_push(*, user_id: str, notification_type: str, preview: str) -> None:
    logger.info(
        "(stub) would send FCM push to user=%s type=%s preview=%r — "
        "no Firebase project configured (architecture.md §9, §10)",
        user_id,
        notification_type,
        preview,
    )
