# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth import get_current_user, verify_csrf
from app.database import get_db
from app.models import User
from app.schemas import VerificationCreate, VerificationResponse
from app.services.verification_service import submit_verification

router = APIRouter(prefix="/api/verifications", tags=["Verifications"])


@router.post("", response_model=VerificationResponse)
def verify_issue(
    payload: VerificationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(verify_csrf),
):
    return submit_verification(
        db=db,
        issue_id=payload.issue_id,
        verifier=current_user,
        ip_address=request.client.host if request.client else None,
    )
