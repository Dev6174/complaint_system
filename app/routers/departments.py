# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import RoleChecker, get_current_user, verify_csrf
from app.database import get_db
from app.models import Issue, User
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/departments", tags=["Departments"])

DEPARTMENTS = [
    "Roads & Transportation",
    "Water Supply Department",
    "Electricity Department",
    "Sanitation & Waste Management",
    "Public Safety & Police",
    "Public Works Department",
    "General Services"
]

@router.get("")
def list_departments(current_user: User = Depends(get_current_user)):
    return {"departments": DEPARTMENTS}

@router.post("/assign")
def assign_department(
    issue_id: int,
    department: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Staff", "Admin"])),
    _=Depends(verify_csrf)
):
    if department not in DEPARTMENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid department. Must be one of: {DEPARTMENTS}"
        )

    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    old_dept = issue.assigned_department
    issue.assigned_department = department

    # Auto transition to "In Progress" if still Open
    old_status = issue.status
    if issue.status == "Open":
        issue.status = "In Progress"

    db.commit()

    log_action(
        db,
        user_id=current_user.id,
        action="ISSUE_ASSIGNED",
        details={
            "issue_id": issue.id,
            "old_department": old_dept,
            "new_department": department,
            "old_status": old_status,
            "new_status": issue.status
        },
        ip_address=request.client.host if request.client else None
    )

    return {"message": f"Issue {issue_id} successfully assigned to {department}."}
