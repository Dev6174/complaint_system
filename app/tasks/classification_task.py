# pyrefly: ignore [missing-import]
import logging
import httpx
from typing import Dict, Any

from app.worker import celery_app
from app.config import settings
from app.classification import classify_issue_local, classification_breaker

logger = logging.getLogger("complaint_system.tasks.classification")

# ---------------------------------------------------------------------------
# Celery task: run_classification
#
# The route handler calls .delay() and immediately returns a task_id to the
# client. The client polls GET /api/issues/classification-result/{task_id}
# until status == "SUCCESS" or "FAILURE".
#
# The circuit breaker (defined in app/classification.py) is reused here —
# it is process-local state, which is fine because each Celery worker process
# maintains its own breaker and falls back to local classification on failure.
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    name="app.tasks.classification_task.run_classification",
    max_retries=2,
    default_retry_delay=5,        # seconds between retries
    soft_time_limit=10,           # raises SoftTimeLimitExceeded after 10s
    time_limit=15,                # hard kill after 15s
    queue="classification",
)
def run_classification(
    self,
    title: str,
    description: str,
    has_attachment: bool = False,
) -> Dict[str, Any]:
    """
    Runs AI classification in a background worker.
    Falls back to local keyword classifier on any failure, matching the
    behaviour of the synchronous version in app/classification.py.
    """
    if not classification_breaker.allow_request() or not settings.AI_CLASSIFIER_API_KEY:
        logger.info("Classification task: using local fallback (circuit breaker open or no API key)")
        return classify_issue_local(title, description)

    try:
        payload = {
            "title": title,
            "description": description,
            "has_attachment": has_attachment,
        }
        headers = {
            "Authorization": f"Bearer {settings.AI_CLASSIFIER_API_KEY}",
            "Content-Type": "application/json",
        }

        # Synchronous httpx inside a Celery task is correct — the worker
        # runs in its own thread/process, not inside the async event loop.
        with httpx.Client(timeout=8.0) as client:
            response = client.post(
                settings.AI_CLASSIFIER_ENDPOINT,
                json=payload,
                headers=headers,
            )

        if response.status_code == 200:
            data = response.json()
            classification_breaker.record_success()
            logger.info(
                "Classification succeeded via external service",
                extra={"title": title[:50]},
            )
            return {
                "category": data.get("category", "Other"),
                "priority": data.get("priority", "Medium"),
                "confidence": float(data.get("confidence", 0.90)),
                "reasoning": data.get("reasoning", "Categorized by automated service."),
            }

        logger.warning(
            "External classification service returned non-200",
            extra={"status_code": response.status_code},
        )
        classification_breaker.record_failure()

    except httpx.TimeoutException as exc:
        logger.error("Classification task timed out", extra={"error": str(exc)})
        classification_breaker.record_failure()
        # Retry up to max_retries before falling back
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            pass

    except Exception as exc:
        logger.error("Classification task failed", extra={"error": str(exc)})
        classification_breaker.record_failure()

    # Graceful fallback — never block issue submission
    return classify_issue_local(title, description)
