# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Issue, Feedback
from app.schemas import FeedbackCreate, FeedbackResponse
from app.auth import get_current_user, verify_csrf
from app.services.feedback_service import submit_feedback, get_feedback_for_issue

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackResponse)
def submit_feedback_route(
    payload: FeedbackCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(verify_csrf),
):
    return submit_feedback(
        db=db,
        issue_id=payload.issue_id,
        reporter=current_user,
        rating=payload.rating,
        comment=payload.comment,
        ip_address=request.client.host if request.client else None,
    )


@router.get("/issue/{issue_id}", response_model=FeedbackResponse)
def get_issue_feedback(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    IDOR fix (Phase 4): previously any authenticated user could read any
    feedback by guessing the issue_id. Now:
    - The reporter of the issue can always read their own feedback.
    - Staff and Admin can read any feedback (for performance dashboards).
    - Other citizens get a 403.
    """
    # Fetch the issue first to check ownership
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    is_staff_or_admin = current_user.role in {"Staff", "Admin"}
    is_reporter = issue.reporter_id == current_user.id

    if not is_staff_or_admin and not is_reporter:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this feedback.",
        )

    return get_feedback_for_issue(db, issue_id)
