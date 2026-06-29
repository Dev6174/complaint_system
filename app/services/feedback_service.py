# pyrefly: ignore [missing-import]
import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User, Issue, Feedback
from app.services.audit_service import log_action
from app.services.gamification import award_points

logger = logging.getLogger("complaint_system.feedback")


def submit_feedback(
    db: Session,
    issue_id: int,
    reporter: User,
    rating: int,
    comment: Optional[str],
    ip_address: Optional[str],
) -> Feedback:
    """
    Submits resolution feedback for a resolved/closed issue.
    Only the original reporter may submit feedback, and only once.
    Automatically closes the issue after feedback is received.
    """
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    if issue.status not in {"Resolved", "Closed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only submit feedback on resolved or closed issues.",
        )

    if issue.reporter_id != reporter.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the reporter of the issue can submit resolution feedback.",
        )

    existing = db.query(Feedback).filter(Feedback.issue_id == issue.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback has already been submitted for this issue.",
        )

    feedback = Feedback(
        issue_id=issue.id,
        user_id=reporter.id,
        rating=rating,
        comment=comment,
    )
    db.add(feedback)
    issue.status = "Closed"

    new_badges = award_points(db, reporter, "submit_feedback")

    db.commit()
    db.refresh(feedback)

    log_action(
        db,
        user_id=reporter.id,
        action="FEEDBACK_SUBMITTED",
        details={
            "feedback_id": feedback.id,
            "issue_id": issue.id,
            "rating": feedback.rating,
            "points_awarded": 5,
            "new_badges": new_badges,
        },
        ip_address=ip_address,
    )

    logger.info(
        "Feedback submitted",
        extra={"feedback_id": feedback.id, "issue_id": issue_id, "rating": rating},
    )
    return feedback


def get_feedback_for_issue(db: Session, issue_id: int) -> Feedback:
    feedback = db.query(Feedback).filter(Feedback.issue_id == issue_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="No feedback found for this issue.")
    return feedback
