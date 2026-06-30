# pyrefly: ignore [missing-import]
import io
from datetime import datetime, timedelta

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import RoleChecker, get_current_user
from app.database import get_db
from app.models import Issue, User
from app.services.cache_service import get_cached, set_cached  # from Phase 2
from app.tasks.report_task import generate_report

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

DASHBOARD_CACHE_KEY = "analytics:dashboard"
DASHBOARD_TTL = 30  # seconds


# ---------------------------------------------------------------------------
# Dashboard — unchanged from Phase 2 (Redis cache already in place)
# ---------------------------------------------------------------------------

@router.get("/dashboard")
def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cached = get_cached(DASHBOARD_CACHE_KEY)
    if cached:
        return cached

    status_counts = dict(
        db.query(Issue.status, func.count(Issue.id)).group_by(Issue.status).all()
    )
    category_counts = dict(
        db.query(Issue.category, func.count(Issue.id)).group_by(Issue.category).all()
    )
    priority_counts = dict(
        db.query(Issue.priority, func.count(Issue.id)).group_by(Issue.priority).all()
    )

    open_map_issues = db.query(Issue).filter(
        Issue.status.in_(["Open", "In Progress", "Reopened"])
    ).all()
    map_data = [
        {
            "id": i.id,
            "title": i.title,
            "category": i.category,
            "priority": i.priority,
            "status": i.status,
            "latitude": i.latitude,
            "longitude": i.longitude,
        }
        for i in open_map_issues
    ]

    resolved_issues = db.query(Issue).filter(
        Issue.status.in_(["Resolved", "Closed"]),
        Issue.resolved_at.isnot(None),
    ).all()
    historical_data: dict = {}
    for issue in resolved_issues:
        key = f"{issue.category}_{issue.priority}"
        duration = (issue.resolved_at - issue.created_at).total_seconds() / 3600.0
        historical_data.setdefault(key, []).append(duration)
    predictions = {k: sum(v) / len(v) for k, v in historical_data.items()}

    three_days_ago = datetime.now() - timedelta(days=3)
    at_risk = db.query(Issue).filter(
        Issue.status.in_(["Open", "In Progress", "Reopened"]),
        Issue.priority.in_(["High", "Urgent"]),
        Issue.created_at < three_days_ago,
    ).all()
    at_risk_list = [
        {
            "id": i.id,
            "title": i.title,
            "category": i.category,
            "priority": i.priority,
            "created_at": i.created_at,
        }
        for i in at_risk
    ]

    result = {
        "status_counts": status_counts,
        "category_counts": category_counts,
        "priority_counts": priority_counts,
        "map_issues": map_data,
        "resolution_predictions": predictions,
        "at_risk_issues": at_risk_list,
    }
    set_cached(DASHBOARD_CACHE_KEY, result, ttl_seconds=DASHBOARD_TTL)
    return result


# ---------------------------------------------------------------------------
# Export — async via Celery
#
# Before (Phase 2): request thread blocked while all rows were fetched and
#   the CSV string was built — could take seconds on large datasets.
#
# After (Phase 3):
#   POST /api/analytics/export?type=summary  → {task_id, status: PENDING}
#   GET  /api/analytics/report-status/{task_id} → poll
#   GET  /api/analytics/report-download/{task_id} → stream CSV when ready
# ---------------------------------------------------------------------------

@router.post("/export")
def request_export(
    report_type: str = Query(..., alias="type"),
    current_user: User = Depends(RoleChecker(["Staff", "Admin"])),
):
    """
    Enqueues a background CSV generation job and returns a task_id immediately.
    """
    valid = {"summary", "pending", "resolved", "department", "feedback"}
    if report_type not in valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report type. Allowed: {sorted(valid)}",
        )
    task = generate_report.delay(report_type)
    return {"task_id": task.id, "status": "PENDING"}


@router.get("/report-status/{task_id}")
def get_report_status(
    task_id: str,
    current_user: User = Depends(RoleChecker(["Staff", "Admin"])),
):
    """Poll the status of a report generation task."""
    result = AsyncResult(task_id)
    if result.state == "SUCCESS":
        data = result.get()
        return {"task_id": task_id, "status": "SUCCESS", "filename": data["filename"]}
    if result.state == "FAILURE":
        return {"task_id": task_id, "status": "FAILURE"}
    return {"task_id": task_id, "status": result.state}


@router.get("/report-download/{task_id}")
def download_report(
    task_id: str,
    current_user: User = Depends(RoleChecker(["Staff", "Admin"])),
):
    """Stream the completed CSV once the task status is SUCCESS."""
    result = AsyncResult(task_id)
    if result.state != "SUCCESS":
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail=f"Report not ready yet. Current status: {result.state}",
        )
    data = result.get()
    stream = io.StringIO(data["csv_content"])
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={data['filename']}"},
    )
