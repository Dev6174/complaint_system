# pyrefly: ignore [missing-import]
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import RoleChecker, get_current_user
from app.database import get_db
from app.models import Feedback, Issue, User
from app.routers.departments import DEPARTMENTS
from app.services.report_writer import (
    generate_department_csv,
    generate_feedback_csv,
    generate_issues_csv,
)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/dashboard")
def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves counts by status, category, priority, maps open issues, and performs predictive analysis.
    """
    # 1. Counts by Status
    status_counts = dict(db.query(Issue.status, func.count(Issue.id)).group_by(Issue.status).all())

    # 2. Counts by Category
    category_counts = dict(db.query(Issue.category, func.count(Issue.id)).group_by(Issue.category).all())

    # 3. Counts by Priority
    priority_counts = dict(db.query(Issue.priority, func.count(Issue.id)).group_by(Issue.priority).all())

    # 4. Map view: Open & In Progress issues
    open_map_issues = db.query(Issue).filter(Issue.status.in_(["Open", "In Progress", "Reopened"])).all()
    map_data = [{
        "id": issue.id,
        "title": issue.title,
        "category": issue.category,
        "priority": issue.priority,
        "status": issue.status,
        "latitude": issue.latitude,
        "longitude": issue.longitude
    } for issue in open_map_issues]

    # 5. Predictive Insight: Expected resolution time from history
    # We group resolved/closed issues by category & priority and calculate average delta (resolved_at - created_at)
    resolved_issues = db.query(Issue).filter(
        Issue.status.in_(["Resolved", "Closed"]),
        Issue.resolved_at.isnot(None)
    ).all()

    # Calculate historical averages in hours
    historical_data = {}  # key: "category_priority" -> list of durations in hours
    for issue in resolved_issues:
        key = f"{issue.category}_{issue.priority}"
        duration = (issue.resolved_at - issue.created_at).total_seconds() / 3600.0
        if key not in historical_data:
            historical_data[key] = []
        historical_data[key].append(duration)

    predictions = {}
    for key, durations in historical_data.items():
        predictions[key] = sum(durations) / len(durations)

    # 6. Flag "At Risk" issues (Older than 3 days, priority High/Urgent, still Open/In Progress)
    three_days_ago = datetime.now() - timedelta(days=3)
    at_risk = db.query(Issue).filter(
        Issue.status.in_(["Open", "In Progress", "Reopened"]),
        Issue.priority.in_(["High", "Urgent"]),
        Issue.created_at < three_days_ago
    ).all()

    at_risk_list = [{
        "id": issue.id,
        "title": issue.title,
        "category": issue.category,
        "priority": issue.priority,
        "created_at": issue.created_at
    } for issue in at_risk]

    return {
        "status_counts": status_counts,
        "category_counts": category_counts,
        "priority_counts": priority_counts,
        "map_issues": map_data,
        "resolution_predictions": predictions,
        "at_risk_issues": at_risk_list
    }

@router.get("/export")
def export_reports(
    report_type: str = Query(..., alias="type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Staff", "Admin"]))
):
    """
    Exports system data to CSV format. Restricted to Staff and Admins.
    """
    if report_type == "summary":
        issues = db.query(Issue).all()
        csv_content = generate_issues_csv(issues)
        filename = "all_issues_summary.csv"

    elif report_type == "pending":
        issues = db.query(Issue).filter(Issue.status.in_(["Open", "In Progress", "Reopened"])).all()
        csv_content = generate_issues_csv(issues)
        filename = "pending_issues.csv"

    elif report_type == "resolved":
        issues = db.query(Issue).filter(Issue.status.in_(["Resolved", "Closed"])).all()
        csv_content = generate_issues_csv(issues)
        filename = "resolved_issues.csv"

    elif report_type == "department":
        # Calculate stats per department
        stats = []
        for dept in DEPARTMENTS:
            total = db.query(Issue).filter(Issue.assigned_department == dept).count()
            resolved = db.query(Issue).filter(
                Issue.assigned_department == dept,
                Issue.status.in_(["Resolved", "Closed"])
            ).count()
            pending = total - resolved

            # Avg feedback rating for this dept
            ratings = db.query(Feedback.rating).join(Issue).filter(
                Issue.assigned_department == dept
            ).all()
            avg_rating = sum([r[0] for r in ratings]) / len(ratings) if ratings else 0.0

            stats.append({
                "department": dept,
                "total": total,
                "resolved": resolved,
                "pending": pending,
                "avg_rating": avg_rating
            })
        csv_content = generate_department_csv(stats)
        filename = "department_performance.csv"

    elif report_type == "feedback":
        feedbacks = db.query(Feedback).all()
        csv_content = generate_feedback_csv(feedbacks)
        filename = "community_feedback.csv"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report type. Allowed: summary, pending, resolved, department, feedback"
        )

    # Return as StreamingResponse
    stream = io.StringIO(csv_content)
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
