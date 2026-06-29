# pyrefly: ignore [missing-import]
import os
import re

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.logging_config import configure_logging
from app.routers import (
    analytics,
    audit,
    auth,
    departments,
    feedback,
    issues,
    leaderboard,
    verification,
)
from app.services.storage_service import get_file_url, is_s3_enabled

# Configure structured logging
configure_logging()

# Schema managed by Alembic — create_all removed
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Complaint System",
    description="A production-grade, full-stack community issue reporting and tracking platform.",
    version="1.0.0"
)

# ---------------------------------------------------------------------------
# CORS — Phase 0: explicit origin allowlist, not wildcard
# ---------------------------------------------------------------------------
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000"
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
)


# ---------------------------------------------------------------------------
# Security headers — Phase 0: tightened CSP, HSTS, Permissions-Policy
# Phase 0 fix 5: Swagger UI / ReDoc get a scoped CSP so cdn.jsdelivr.net
# assets load correctly without weakening the app-wide policy.
# ---------------------------------------------------------------------------
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = (
        "max-age=63072000; includeSubDomains"
    )
    response.headers["Permissions-Policy"] = (
        "geolocation=(self), camera=(), microphone=(), payment=()"
    )

    if request.url.path in DOCS_PATHS:
        # Swagger UI / ReDoc only — looser CSP scoped to docs paths
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://cdn.jsdelivr.net https://fastapi.tiangolo.com; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
    else:
        # App-wide CSP — unsafe-eval removed, object-src/base-uri/form-action added
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com; "
            "img-src 'self' data: blob: https://*.tile.openstreetmap.org https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
    return response


# Register API Routers
app.include_router(auth.router)
app.include_router(issues.router)
app.include_router(verification.router)
app.include_router(departments.router)
app.include_router(feedback.router)
app.include_router(leaderboard.router)
app.include_router(audit.router)
app.include_router(analytics.router)


# ---------------------------------------------------------------------------
# File serving — Phase 4: presigned URL redirect when S3 active
# Local mode: validates filename and serves from disk (unchanged behaviour)
# S3 mode: generates presigned URL and returns 302 redirect — file data
#   never passes through this server, files stay private at rest
# ---------------------------------------------------------------------------
@app.get("/uploads/{filename}")
def serve_upload(filename: str):
    if not re.match(r"^[a-f0-9\-]{36}\.(jpg|jpeg|png|webp|mp4)$", filename.lower()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename format."
        )

    if is_s3_enabled():
        presigned_url = get_file_url(filename)
        return RedirectResponse(url=presigned_url, status_code=302)

    file_path = os.path.join("uploads", filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found."
        )
    return FileResponse(file_path)


# Serve Frontend Static Files — must come last to avoid shadowing API routes
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=5000, reload=True)
