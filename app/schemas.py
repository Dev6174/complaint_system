# pyrefly: ignore [missing-import]
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime

# --- User Schemas ---
class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        # Custom email validation to prevent injection and basic correctness
        import re
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")
        return v.strip().lower()

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="Citizen")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = ["Citizen", "Staff", "Admin"]
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v

class UserLogin(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., max_length=128)

class PasswordChange(BaseModel):
    old_password: str = Field(..., max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    points: int
    badges: List[str] = []
    created_at: datetime

    @field_validator("badges", mode="before")
    @classmethod
    def parse_badges(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except Exception:
                return []
        return v or []

    class Config:
        from_attributes = True

# --- Issue Schemas ---
class IssueBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=150)
    description: str = Field(..., min_length=10, max_length=1000)
    category: str = Field(..., min_length=2, max_length=100)
    priority: str = Field(..., min_length=3, max_length=20)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        allowed = ["Low", "Medium", "High", "Urgent"]
        if v not in allowed:
            raise ValueError(f"Priority must be one of {allowed}")
        return v

class IssueCreate(IssueBase):
    pass

class IssueUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=150)
    description: Optional[str] = Field(None, min_length=10, max_length=1000)
    category: Optional[str] = Field(None, min_length=2, max_length=100)
    priority: Optional[str] = Field(None, min_length=3, max_length=20)
    status: Optional[str] = Field(None)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = ["Low", "Medium", "High", "Urgent"]
        if v not in allowed:
            raise ValueError(f"Priority must be one of {allowed}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = ["Open", "In Progress", "Resolved", "Closed", "Reopened"]
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v

class IssueResolve(BaseModel):
    resolution_notes: str = Field(..., min_length=5, max_length=1000)

class IssueResponse(BaseModel):
    id: int
    reporter_id: int
    reporter_name: Optional[str] = None
    title: str
    description: str
    category: str
    priority: str
    latitude: float
    longitude: float
    status: str
    attachment_filename: Optional[str]
    verification_count: int
    assigned_department: Optional[str]
    resolution_notes: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

# --- Verification Schemas ---
class VerificationCreate(BaseModel):
    issue_id: int

class VerificationResponse(BaseModel):
    id: int
    issue_id: int
    user_id: int
    verified_at: datetime

    class Config:
        from_attributes = True

# --- Feedback Schemas ---
class FeedbackCreate(BaseModel):
    issue_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)

class FeedbackResponse(BaseModel):
    id: int
    issue_id: int
    user_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# --- Audit Log Schemas ---
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    user_name: Optional[str] = None
    action: str
    details: str
    ip_address: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True
