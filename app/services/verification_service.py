# pyrefly: ignore [missing-import]
import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, Issue, Verification
from app.services.audit_service import log_action
from app.services.gamification import award_points
from app.tasks.notification_task import send_notification, NOTIF_ESCALATED, NOTIF_VERIFIED

logger = logging.getLogger("complaint_system.verification")

DEPARTMENT_MAPPING = {
    "Potholes": "Roads & Transportation",
    "Water Leakage": "Water Supply Department",
    "Damaged Streetlights": "Electricity Department",
    "Waste Management": "Sanitation & Waste Management",
    "Public Safety Hazards": "Public Safety & Police",
    "Infrastructure Problems": "Public Works Department",
}

PRIORITY_LADDER = ["Low", "Medium", "High", "Urgent"]


def _escalate_priority(current: str) -> str:
    try:
        idx = PRIORITY_LADDER.index(current)
    except ValueError:
        return "Medium"
    return PRIORITY_LADDER[min(idx + 1, len(PRIORITY_LADDER) - 1)]


def submit_verification(
    db: Session,
    issue_id: int,
    verifier: User,
    ip_address: Optional[str],
) -> Verification:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    if issue.reporter_id == verifier.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot verify your own reported issues.",
        )

    existing = (
        db.query(Verification)
        .filter(Verification.issue_id == issue.id, Verification.user_id == verifier.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already verified this issue.",
        )

    verification = Verification(issue_id=issue.id, user_id=verifier.id)
    db.add(verification)

    issue.verification_count += 1
    old_priority = issue.priority
    escalated = False

    if issue.verification_count == settings.VERIFICATION_THRESHOLD:
        issue.priority = _escalate_priority(issue.priority)
        dept = DEPARTMENT_MAPPING.get(issue.category, "General Services")
        if issue.assigned_department != dept:
            issue.assigned_department = dept
        escalated = True

    new_badges = award_points(db, verifier, "verify_issue")

    db.commit()
    db.refresh(verification)
    db.refresh(issue)

    log_action(
        db,
        user_id=verifier.id,
        action="ISSUE_VERIFIED",
        details={
            "verification_id": verification.id,
            "issue_id": issue.id,
            "new_count": issue.verification_count,
            "escalated": escalated,
            "old_priority": old_priority,
            "new_priority": issue.priority,
            "assigned_department": issue.assigned_department,
            "points_awarded": 2,
            "new_badges": new_badges,
        },
        ip_address=ip_address,
    )

    # Fire notification to the reporter — async, does not block the response
    send_notification.delay(
        recipient_user_id=issue.reporter_id,
        event_type=NOTIF_ESCALATED if escalated else NOTIF_VERIFIED,
        issue_id=issue.id,
        message=(
            f"Your issue #{issue.id} has been escalated to {issue.priority} priority "
            f"and assigned to {issue.assigned_department}."
            if escalated
            else f"Your issue #{issue.id} received a new community verification "
                 f"({issue.verification_count} total)."
        ),
    )

    logger.info(
        "Issue verified",
        extra={
            "issue_id": issue_id,
            "verifier_id": verifier.id,
            "count": issue.verification_count,
            "escalated": escalated,
        },
    )
    return verification
