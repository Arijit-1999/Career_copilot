"""SQLAlchemy database models for Tailored Resumes and Master Resume versions."""

import uuid
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    String,
    Text,
    Float,
    Boolean,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.resumes.enums import ResumeStatus, ResumeFormat


class TailoredResume(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persists generated Master or JD-Targeted Resumes."""

    __tablename__ = "tailored_resumes"
    __table_args__ = (
        Index("ix_tailored_resumes_candidate_master", "candidate_id", "is_master"),
        Index("ix_tailored_resumes_job_id", "job_id"),
        Index("ix_tailored_resumes_status", "status"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    target_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Rendered Content
    raw_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    structured_content: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    targeted_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    # Flags & Quality Scores
    is_master: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[ResumeStatus] = mapped_column(
        SQLEnum(ResumeStatus, native_enum=False, length=50),
        default=ResumeStatus.VERIFIED_TAILORED,
        nullable=False
    )
    truth_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    validation_report: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    user_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile")
    job: Mapped[Optional["Job"]] = relationship("Job")
