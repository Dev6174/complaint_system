# pyrefly: ignore [missing-import]
# Phase 4 update to app/services/issue_service.py
#
# Changes vs Phase 1/3:
#   1. validate_and_save_upload now uses storage_service.save_file()
#      instead of writing directly to local disk. Works transparently
#      with both S3/MinIO and local disk depending on env config.
#   2. get_attachment_url() helper added — returns presigned URL (S3)
#      or local route (disk) depending on backend.
#   3. All other functions unchanged.

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.models import AuditLog, Issue, User
from app.services.audit_service import log_action
from app.services.gamification import award_points
from app.services.storage_service import get_file_url, save_file

logger = logging.getLogger("complaint_system.issues")

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "video/mp4"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".mp4"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ---------------------------------------------------------------------------
# File validation + storage (Phase 4: storage backend abstracted)
# ---------------------------------------------------------------------------

def validate_and_save_upload(file: UploadFile) -> str:
    """
    Validates extension, MIME type, size, and magic bytes.
    Saves via storage_service (S3/MinIO or local disk).
    Returns the storage key stored in the DB.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported MIME type. Allowed: {sorted(ALLOWED_MIME_TYPES)}",
        )

    content = file.file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 10 MB limit.",
        )
    file.file.seek(0)

    # Magic byte checks
    if ext == ".png" and not content.startswith(b"\x89PNG"):
        raise HTTPException(status_code=400, detail="Invalid PNG file headers.")
    if ext in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=400, detail="Invalid JPEG file headers.")
    if ext == ".mp4" and b"ftyp" not in content[0:20]:
        raise HTTPException(status_code=400, detail="Invalid MP4 video file headers.")

    # Delegate storage to the storage service — local disk or S3/MinIO
    filename = save_file(content, ext)
    logger.info("File upload validated and saved", extra={"filename": filename, "ext": ext})
    return filename


def get_attachment_url(filename: str, request_base_url: str = "") -> str | None:
    """
    Returns a time-limited presigned URL (S3) or a local serve URL.
    Call this when building issue responses that include attachments.
    """
    if not filename:
        return None
    return get_file_url(filename, request_base_url)


# ---------------------------------------------------------------------------
# Issue creation
# ---------------------------------------------------------------------------

def create_issue(
    db: Session,
    reporter: User,
    title: str,
    description: str,
    category: str,
    priority: str,
    latitude: float,
    longitude: float,
    attachment_filename: str | None,
    ip_address: str | None,
) -> Issue:
    if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
        raise HTTPException(
            status_code=400,
            detail="Latitude must be −90 to 90 and longitude −180 to 180.",
        )
    if len(title) < 5 or len(description) < 10:
        raise HTTPException(
            status_code=400,
            detail="Title (min 5 chars) or description (min 10 chars) too short.",
        )

    issue = Issue(
        reporter_id=reporter.id,
        title=title,
        description=description,
        category=category,
        priority=priority,
        latitude=latitude,
        longitude=longitude,
        status="Open",
        attachment_filename=attachment_filename,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)

    newly_unlocked = award_points(db, reporter, "report_issue")

    log_action(
        db,
        user_id=reporter.id,
        action="ISSUE_REPORTED",
        details={
            "issue_id": issue.id,
            "title": issue.title,
            "category": issue.category,
            "priority": issue.priority,
            "points_awarded": 10,
            "newly_unlocked_badges": newly_unlocked,
        },
        ip_address=ip_address,
    )

    logger.info(
        "Issue created",
        extra={"issue_id": issue.id, "reporter_id": reporter.id, "category": category},
    )
    return issue


# ---------------------------------------------------------------------------
# Issue listing
# ---------------------------------------------------------------------------

def list_issues(
    db: Session,
    search: str | None,
    category: str | None,
    priority: str | None,
    status_filter: str | None,
    sort_by: str,
    order: str,
    page: int,
    limit: int,
) -> dict[str, Any]:
    query = db.query(Issue)

    if category:
        query = query.filter(Issue.category == category)
    if priority:
        query = query.filter(Issue.priority == priority)
    if status_filter:
        query = query.filter(Issue.status == status_filter)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Issue.title.like(term),
                Issue.description.like(term),
                Issue.id.like(term),
            )
        )

    sort_col = getattr(Issue, sort_by, Issue.created_at)
    query = query.order_by(desc(sort_col) if order == "desc" else asc(sort_col))

    total = query.count()
    results = query.offset((page - 1) * limit).limit(limit).all()

    reporter_ids = {i.reporter_id for i in results}
    reporters = {
        u.id: u.name
        for u in db.query(User).filter(User.id.in_(reporter_ids)).all()
    }

    issues_list = [
        {
            "id": i.id,
            "reporter_id": i.reporter_id,
            "reporter_name": reporters.get(i.reporter_id, "Unknown"),
            "title": i.title,
            "description": i.description,
            "category": i.category,
            "priority": i.priority,
            "latitude": i.latitude,
            "longitude": i.longitude,
            "status": i.status,
            "attachment_filename": i.attachment_filename,
            "verification_count": i.verification_count,
            "assigned_department": i.assigned_department,
            "resolution_notes": i.resolution_notes,
            "resolved_at": i.resolved_at,
            "created_at": i.created_at,
        }
        for i in results
    ]

    return {"total": total, "page": page, "limit": limit, "issues": issues_list}


# ---------------------------------------------------------------------------
# Single issue fetch
# ---------------------------------------------------------------------------

def get_issue(db: Session, issue_id: int) -> Issue:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")
    reporter = db.query(User).filter(User.id == issue.reporter_id).first()
    issue.reporter_name = reporter.name if reporter else "Unknown"
    return issue


# ---------------------------------------------------------------------------
# Issue update
# ---------------------------------------------------------------------------

def update_issue(
    db: Session,
    issue_id: int,
    update_data: dict[str, Any],
    current_user: User,
    ip_address: str | None,
) -> Issue:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    is_staff_or_admin = current_user.role in {"Staff", "Admin"}

    if not is_staff_or_admin:
        if issue.reporter_id != current_user.id:
            raise HTTPException(status_code=403, detail="You do not own this issue report.")
        if issue.status != "Open":
            raise HTTPException(
                status_code=400,
                detail="Cannot edit an issue that is already in progress or resolved.",
            )
        if "status" in update_data:
            if update_data["status"] == "Reopened" and issue.status == "Resolved":
                pass
            else:
                raise HTTPException(status_code=403, detail="Citizens cannot set this status.")

    old_status = issue.status
    for key, value in update_data.items():
        setattr(issue, key, value)

    log_action(
        db,
        user_id=current_user.id,
        action="ISSUE_UPDATED",
        details={
            "issue_id": issue.id,
            "changes": update_data,
            "old_status": old_status,
            "new_status": issue.status,
        },
        ip_address=ip_address,
    )

    db.commit()
    db.refresh(issue)
    return issue


# ---------------------------------------------------------------------------
# Issue resolution (with notification — from Phase 3)
# ---------------------------------------------------------------------------

def resolve_issue(
    db: Session,
    issue_id: int,
    resolution_notes: str,
    resolver: User,
    ip_address: str | None,
) -> Issue:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")
    if issue.status in {"Resolved", "Closed"}:
        raise HTTPException(status_code=400, detail="Issue is already resolved or closed.")

    issue.status = "Resolved"
    issue.resolution_notes = resolution_notes
    issue.resolved_at = datetime.now(UTC)

    reporter = db.query(User).filter(User.id == issue.reporter_id).first()
    reporter_new_badges: list[str] = []
    if reporter:
        reporter_new_badges = award_points(db, reporter, "issue_resolved_bonus")

    log_action(
        db,
        user_id=resolver.id,
        action="ISSUE_RESOLVED",
        details={
            "issue_id": issue.id,
            "notes": resolution_notes,
            "reporter_id": issue.reporter_id,
            "bonus_points_awarded": 15,
            "reporter_newly_unlocked_badges": reporter_new_badges,
        },
        ip_address=ip_address,
    )

    db.commit()
    db.refresh(issue)

    from app.tasks.notification_task import NOTIF_RESOLVED, send_notification
    send_notification.delay(
        recipient_user_id=issue.reporter_id,
        event_type=NOTIF_RESOLVED,
        issue_id=issue.id,
        message=(
            f"Your issue #{issue.id} '{issue.title}' has been resolved. "
            "Please leave feedback to help us improve."
        ),
    )

    logger.info("Issue resolved", extra={"issue_id": issue_id, "resolver_id": resolver.id})
    return issue


# ---------------------------------------------------------------------------
# Issue history
# ---------------------------------------------------------------------------

def get_issue_history(db: Session, issue_id: int) -> list[dict[str, Any]]:
    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.details.like(f'%"issue_id": {issue_id}%')
            | AuditLog.details.like(f'%"issue_id": "{issue_id}"%')
        )
        .order_by(asc(AuditLog.timestamp))
        .all()
    )

    history = []
    for log in logs:
        try:
            details_json = json.loads(log.details)
        except Exception:
            details_json = {}
        history.append(
            {"action": log.action, "timestamp": log.timestamp, "details": details_json}
        )
    return history
