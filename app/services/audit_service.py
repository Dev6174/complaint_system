# pyrefly: ignore [missing-import]
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def log_action(db: Session, user_id: int | None, action: str, details: Any, ip_address: str | None = None):
    """
    Logs an immutable record to the audit trail table.
    """
    if isinstance(details, (dict, list)):
        details_str = json.dumps(details)
    else:
        details_str = str(details)

    audit_record = AuditLog(
        user_id=user_id,
        action=action,
        details=details_str,
        ip_address=ip_address
    )
    db.add(audit_record)
    db.commit()
