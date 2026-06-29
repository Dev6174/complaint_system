# pyrefly: ignore [missing-import]
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.models import User
from app.services.audit_service import log_action

logger = logging.getLogger("complaint_system.auth")


def create_user(
    db: Session,
    name: str,
    email: str,
    password: str,
    requested_role: str,
    ip_address: str | None,
) -> User:
    """
    Registers a new user. First user in the system is automatically Admin.
    Raises HTTPException on duplicate email.
    """
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    # First user bootstraps as Admin for initial setup convenience
    role = "Admin" if db.query(User).count() == 0 else requested_role

    new_user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_action(
        db,
        user_id=new_user.id,
        action="USER_REGISTRATION",
        details={"email": new_user.email, "role": new_user.role},
        ip_address=ip_address,
    )

    logger.info(
        "User registered",
        extra={"user_id": new_user.id, "email": new_user.email, "role": role},
    )
    return new_user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
    ip_address: str | None,
) -> tuple[User, str]:
    """
    Verifies credentials and returns (user, access_token).
    Raises HTTPException on failure — caller is responsible for rate-limit
    tracking so it can record failures before raising.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    access_token = create_access_token(data={"sub": user.email, "role": user.role})

    log_action(
        db,
        user_id=user.id,
        action="USER_LOGIN",
        details={"email": user.email},
        ip_address=ip_address,
    )

    logger.info("User logged in", extra={"user_id": user.id, "email": user.email})
    return user, access_token


def change_user_password(
    db: Session,
    user: User,
    old_password: str,
    new_password: str,
    ip_address: str | None,
) -> None:
    """
    Validates old password and updates hash.
    Raises HTTPException if old password is wrong.
    """
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password.",
        )

    user.password_hash = hash_password(new_password)
    db.commit()

    log_action(
        db,
        user_id=user.id,
        action="PASSWORD_CHANGE",
        details={"email": user.email},
        ip_address=ip_address,
    )

    logger.info("Password changed", extra={"user_id": user.id})
