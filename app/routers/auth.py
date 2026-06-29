# pyrefly: ignore [missing-import]
import secrets

from fastapi import APIRouter, Depends, Response, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, UserResponse, PasswordChange
from app.auth import get_current_user, verify_csrf
from app.rate_limiter import rate_limit_ip, is_rate_limited
from app.services.audit_service import log_action
from app.services.auth_service import create_user, authenticate_user, change_user_password

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

LOGIN_LIMIT = settings.RATE_LIMIT_LOGIN_MAX
WINDOW = settings.RATE_LIMIT_WINDOW_SECONDS


def _set_auth_cookies(response: Response, access_token: str) -> str:
    """Sets the HttpOnly access token cookie and returns a fresh CSRF token."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production (HTTPS)
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    csrf_token = secrets.token_hex(32)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        samesite="lax",
        secure=False,
        httponly=False,  # Must be readable by JS for double-submit pattern
    )
    return csrf_token


@router.get("/csrf")
def get_csrf_token(response: Response):
    csrf_token = secrets.token_hex(32)
    response.set_cookie(key="csrf_token", value=csrf_token, samesite="lax", secure=False, httponly=False)
    return {"csrf_token": csrf_token}


@router.post("/signup", response_model=UserResponse)
def signup(
    user_in: UserCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _=Depends(rate_limit_ip(max_requests=10, window_seconds=60)),
):
    ip = request.client.host if request.client else None
    new_user = create_user(
        db=db,
        name=user_in.name,
        email=user_in.email,
        password=user_in.password,
        requested_role=user_in.role,
        ip_address=ip,
    )
    # Issue a CSRF cookie so the client can immediately make state-changing requests
    csrf_token = secrets.token_hex(32)
    response.set_cookie(key="csrf_token", value=csrf_token, samesite="lax", secure=False, httponly=False)
    return new_user


@router.post("/login")
def login(
    user_in: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _=Depends(rate_limit_ip(max_requests=10, window_seconds=60)),
):
    ip = request.client.host if request.client else None
    email_clean = user_in.email.strip().lower()
    fail_key = f"login_fail:{email_clean}"

    # Pre-check lockout before attempting auth
    if is_rate_limited(fail_key, LOGIN_LIMIT, WINDOW):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account locked due to multiple failed login attempts. Please try again in 1 minute.",
        )

    try:
        user, access_token = authenticate_user(db, email_clean, user_in.password, ip)
    except Exception:
        # Record failure then re-raise
        is_rate_limited(fail_key, LOGIN_LIMIT, WINDOW)
        raise

    # Clear failure counter on success
    from app.rate_limiter import _rate_limit_cache
    _rate_limit_cache[fail_key] = []

    csrf_token = _set_auth_cookies(response, access_token)

    return {
        "message": "Login successful",
        "csrf_token": csrf_token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "points": user.points,
        },
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response.delete_cookie("access_token")
    response.delete_cookie("csrf_token")
    log_action(
        db,
        user_id=current_user.id,
        action="USER_LOGOUT",
        details={"email": current_user.email},
        ip_address=request.client.host if request.client else None,
    )
    return {"message": "Logout successful"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
def change_password(
    payload: PasswordChange,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(verify_csrf),
):
    change_user_password(
        db=db,
        user=current_user,
        old_password=payload.old_password,
        new_password=payload.new_password,
        ip_address=request.client.host if request.client else None,
    )
    response.delete_cookie("access_token")
    response.delete_cookie("csrf_token")
    return {"message": "Password changed successfully. Please log in again."}
