# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import RoleChecker
from app.database import get_db
from app.models import AuditLog, User
from app.schemas import AuditLogResponse

router = APIRouter(prefix="/api/audit", tags=["Audit Log"])


@router.get("", response_model=list[AuditLogResponse])
def get_audit_trail(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Admin"])),
):
    """
    Returns immutable audit logs, ordered by timestamp descending.
    Admin only.

    Phase 4 fix: original code ran one extra DB query per log entry to
    fetch the user name (N+1). Now batch-loads all users in one query.
    """
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )

    # Batch load user names — one query instead of one per log entry
    user_ids = {log.user_id for log in logs if log.user_id}
    users = {
        u.id: u.name
        for u in db.query(User).filter(User.id.in_(user_ids)).all()
    }

    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "user_name": users.get(log.user_id, "System") if log.user_id else "System",
            "action": log.action,
            "details": log.details,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp,
        }
        for log in logs
    ]
