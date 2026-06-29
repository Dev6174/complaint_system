# pyrefly: ignore [missing-import]

from celery.result import AsyncResult
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    Request,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.auth import RoleChecker, get_current_user, verify_csrf
from app.database import get_db
from app.models import User
from app.rate_limiter import rate_limit_ip
from app.schemas import IssueResolve, IssueResponse, IssueUpdate
from app.services.issue_service import (
    create_issue,
    get_issue,
    get_issue_history,
    list_issues,
    resolve_issue,
    update_issue,
    validate_and_save_upload,
)
from app.tasks.classification_task import run_classification

router = APIRouter(prefix="/api/issues", tags=["Issues"])


# ---------------------------------------------------------------------------
# Classification — now async via Celery
# POST  /api/issues/suggest-classification  → returns task_id immediately
# GET   /api/issues/classification-result/{task_id} → poll for result
# ---------------------------------------------------------------------------

@router.post("/suggest-classification")
async def suggest_classification(
    title: str = Form(...),
    description: str = Form(...),
    current_user: User = Depends(get_current_user),
    _=Depends(rate_limit_ip(max_requests=10, window_seconds=60)),
):
    """
    Enqueues a background classification job and returns a task_id.
    The client should poll /suggest-classification/result/{task_id}.
    Falls back to local classifier automatically if the worker is unavailable.
    """
    task = run_classification.delay(title=title, description=description)
    return {"task_id": task.id, "status": "PENDING"}


@router.get("/classification-result/{task_id}")
def get_classification_result(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Polls the result of a classification task.
    Returns status: PENDING | SUCCESS | FAILURE and result when ready.
    """
    result = AsyncResult(task_id)

    if result.state == "PENDING":
        return {"task_id": task_id, "status": "PENDING"}

    if result.state == "SUCCESS":
        return {"task_id": task_id, "status": "SUCCESS", "result": result.get()}

    if result.state == "FAILURE":
        return {"task_id": task_id, "status": "FAILURE", "result": None}

    return {"task_id": task_id, "status": result.state}


# ---------------------------------------------------------------------------
# Issue CRUD — unchanged from Phase 1
# ---------------------------------------------------------------------------

@router.post("", response_model=IssueResponse)
async def report_issue(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    priority: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _csrf=Depends(verify_csrf),
    _rate=Depends(rate_limit_ip(max_requests=5, window_seconds=60)),
):
    attachment_name = None
    if file and file.filename:
        attachment_name = validate_and_save_upload(file)

    return create_issue(
        db=db,
        reporter=current_user,
        title=title,
        description=description,
        category=category,
        priority=priority,
        latitude=latitude,
        longitude=longitude,
        attachment_filename=attachment_name,
        ip_address=request.client.host if request.client else None,
    )


@router.get("", response_model=dict)
def get_issues(
    search: str | None = Query(None),
    category: str | None = Query(None),
    priority: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_issues(
        db=db,
        search=search,
        category=category,
        priority=priority,
        status_filter=status_filter,
        sort_by=sort_by,
        order=order,
        page=page,
        limit=limit,
    )


@router.get("/{issue_id}", response_model=IssueResponse)
def get_issue_by_id(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_issue(db, issue_id)


@router.put("/{issue_id}", response_model=IssueResponse)
def update_issue_route(
    issue_id: int,
    payload: IssueUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(verify_csrf),
):
    return update_issue(
        db=db,
        issue_id=issue_id,
        update_data=payload.model_dump(exclude_unset=True),
        current_user=current_user,
        ip_address=request.client.host if request.client else None,
    )


@router.post("/{issue_id}/resolve", response_model=IssueResponse)
def resolve_issue_route(
    issue_id: int,
    payload: IssueResolve,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["Staff", "Admin"])),
    _=Depends(verify_csrf),
):
    return resolve_issue(
        db=db,
        issue_id=issue_id,
        resolution_notes=payload.resolution_notes,
        resolver=current_user,
        ip_address=request.client.host if request.client else None,
    )


@router.get("/{issue_id}/history", response_model=list)
def issue_history(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_issue_history(db, issue_id)
