# pyrefly: ignore [missing-import]
import logging

from app.worker import celery_app

logger = logging.getLogger("complaint_system.tasks.report")

# ---------------------------------------------------------------------------
# Report generation task
#
# The /api/analytics/export endpoint previously blocked the request thread
# while querying all rows and building a CSV string. On large datasets this
# can take several seconds. This task runs the same logic in a background
# worker and stores the result in the Celery result backend (Redis).
#
# The API returns a task_id immediately. The client polls
# GET /api/analytics/report-status/{task_id} until done, then downloads
# the CSV from GET /api/analytics/report-download/{task_id}.
# ---------------------------------------------------------------------------

VALID_REPORT_TYPES = {"summary", "pending", "resolved", "department", "feedback"}


@celery_app.task(
    name="app.tasks.report_task.generate_report",
    max_retries=1,
    soft_time_limit=60,   # CSV generation should finish well within 60s
    time_limit=90,
    queue="reports",
)
def generate_report(report_type: str) -> dict:
    """
    Generates a CSV report and stores the content string in the result backend.
    Returns {"filename": str, "csv_content": str} on success.
    """
    if report_type not in VALID_REPORT_TYPES:
        raise ValueError(f"Invalid report type: {report_type}. Allowed: {VALID_REPORT_TYPES}")

    # Import here to avoid importing the full app at module load time in the worker
    from app.database import SessionLocal
    from app.models import Feedback, Issue
    from app.routers.departments import DEPARTMENTS
    from app.services.report_writer import (
        generate_department_csv,
        generate_feedback_csv,
        generate_issues_csv,
    )

    db = SessionLocal()
    try:
        if report_type == "summary":
            issues = db.query(Issue).all()
            csv_content = generate_issues_csv(issues)
            filename = "all_issues_summary.csv"

        elif report_type == "pending":
            issues = db.query(Issue).filter(
                Issue.status.in_(["Open", "In Progress", "Reopened"])
            ).all()
            csv_content = generate_issues_csv(issues)
            filename = "pending_issues.csv"

        elif report_type == "resolved":
            issues = db.query(Issue).filter(
                Issue.status.in_(["Resolved", "Closed"])
            ).all()
            csv_content = generate_issues_csv(issues)
            filename = "resolved_issues.csv"

        elif report_type == "department":
            stats = []
            for dept in DEPARTMENTS:
                total = db.query(Issue).filter(Issue.assigned_department == dept).count()
                resolved = db.query(Issue).filter(
                    Issue.assigned_department == dept,
                    Issue.status.in_(["Resolved", "Closed"]),
                ).count()
                ratings = (
                    db.query(Feedback.rating)
                    .join(Issue)
                    .filter(Issue.assigned_department == dept)
                    .all()
                )
                avg_rating = sum(r[0] for r in ratings) / len(ratings) if ratings else 0.0
                stats.append({
                    "department": dept,
                    "total": total,
                    "resolved": resolved,
                    "pending": total - resolved,
                    "avg_rating": avg_rating,
                })
            csv_content = generate_department_csv(stats)
            filename = "department_performance.csv"

        elif report_type == "feedback":
            feedbacks = db.query(Feedback).all()
            csv_content = generate_feedback_csv(feedbacks)
            filename = "community_feedback.csv"

        logger.info(
            "Report generated",
            extra={"report_type": report_type, "filename": filename},
        )
        return {"filename": filename, "csv_content": csv_content}

    finally:
        db.close()
