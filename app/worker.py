# pyrefly: ignore [missing-import]
import logging

from celery import Celery

from app.config import settings

logger = logging.getLogger("complaint_system.worker")

# ---------------------------------------------------------------------------
# Celery application
# Broker: Redis (same Upstash instance used for caching in Phase 2)
# Backend: Redis (stores task results so the API can poll them)
# ---------------------------------------------------------------------------
celery_app = Celery(
    "complaint_system",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.classification_task",
        "app.tasks.notification_task",
        "app.tasks.report_task",
    ],
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Results expire after 1 hour — enough for polling, avoids Redis bloat
    result_expires=3600,

    # Retry behaviour defaults for all tasks
    task_acks_late=True,               # Ack only after task completes (safer on worker crash)
    task_reject_on_worker_lost=True,   # Re-queue if worker dies mid-task

    # Rate limit the classification queue so a burst of submissions
    # cannot hammer the external categorization service
    task_routes={
        "app.tasks.classification_task.run_classification": {"queue": "classification"},
        "app.tasks.notification_task.send_notification": {"queue": "notifications"},
        "app.tasks.report_task.generate_report": {"queue": "reports"},
    },
)
