# pyrefly: ignore [missing-import]
import logging

from app.worker import celery_app

logger = logging.getLogger("complaint_system.tasks.notification")

# ---------------------------------------------------------------------------
# Notification event types — kept as constants so callers never use raw strings
# ---------------------------------------------------------------------------
NOTIF_STATUS_CHANGED = "STATUS_CHANGED"
NOTIF_VERIFIED = "ISSUE_VERIFIED"
NOTIF_RESOLVED = "ISSUE_RESOLVED"
NOTIF_ESCALATED = "ISSUE_ESCALATED"


@celery_app.task(
    name="app.tasks.notification_task.send_notification",
    max_retries=3,
    default_retry_delay=10,
    queue="notifications",
)
def send_notification(
    recipient_user_id: int,
    event_type: str,
    issue_id: int,
    message: str,
    extra: dict | None = None,
) -> dict:
    """
    Delivers an in-app notification to a specific user.

    Currently writes structured log entries that the frontend can poll via
    a future /api/notifications endpoint. Replace the log call with DB
    writes or a WebSocket push once the Notification model is added in
    Phase 4 (Officer UX).

    Targeted delivery: recipient_user_id ensures only the correct user
    receives the notification — not a broadcast to everyone.
    """
    logger.info(
        "Notification dispatched",
        extra={
            "recipient_user_id": recipient_user_id,
            "event_type": event_type,
            "issue_id": issue_id,
            "message": message,
            **(extra or {}),
        },
    )

    # ------------------------------------------------------------------
    # TODO (Phase 4): Replace the logger call above with:
    #
    #   from app.database import SessionLocal
    #   from app.models import Notification
    #   db = SessionLocal()
    #   try:
    #       notif = Notification(
    #           user_id=recipient_user_id,
    #           event_type=event_type,
    #           issue_id=issue_id,
    #           message=message,
    #       )
    #       db.add(notif)
    #       db.commit()
    #   finally:
    #       db.close()
    #
    # The Celery task signature stays identical — no changes needed in
    # the callers when the implementation is swapped.
    # ------------------------------------------------------------------

    return {
        "delivered": True,
        "recipient_user_id": recipient_user_id,
        "event_type": event_type,
        "issue_id": issue_id,
    }
