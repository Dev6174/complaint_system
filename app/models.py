# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="Citizen", nullable=False)  # Citizen, Staff, Admin
    points = Column(Integer, default=0, nullable=False)
    badges = Column(Text, default="[]", nullable=False)  # JSON serialized array of strings
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    reported_issues = relationship("Issue", back_populates="reporter", foreign_keys="[Issue.reporter_id]")
    verifications = relationship("Verification", back_populates="user")
    feedbacks = relationship("Feedback", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), index=True, nullable=False)
    priority = Column(String(50), index=True, nullable=False)  # Low, Medium, High, Urgent
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String(50), index=True, default="Open", nullable=False)  # Open, In Progress, Resolved, Closed, Reopened
    attachment_filename = Column(String(255), nullable=True)
    verification_count = Column(Integer, default=0, nullable=False)
    assigned_department = Column(String(100), index=True, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    reporter = relationship("User", back_populates="reported_issues", foreign_keys=[reporter_id])
    verifications = relationship("Verification", back_populates="issue", cascade="all, delete-orphan")
    feedback = relationship("Feedback", uselist=False, back_populates="issue", cascade="all, delete-orphan")


class Verification(Base):
    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    verified_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    issue = relationship("Issue", back_populates="verifications")
    user = relationship("User", back_populates="verifications")

    __table_args__ = (
        UniqueConstraint("issue_id", "user_id", name="uq_issue_user_verification"),
    )


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id", ondelete="CASCADE"), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1 to 5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    issue = relationship("Issue", back_populates="feedback")
    user = relationship("User", back_populates="feedbacks")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=False)  # Descriptive string or JSON dump
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
