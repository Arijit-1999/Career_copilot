"""SQLAlchemy ORM model for tracked job applications."""

import uuid
from typing import Optional, Dict, Any

from sqlalchemy import (
    String,
    Text,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    Index,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.applications.enums import ApplicationStatus


class JobApplication(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks the full lifecycle of a candidate's job application."""

    __tablename__ = "job_applications"
    __table_args__ = (
        Index("ix_job_applications_candidate_id", "candidate_id"),
        Index("ix_job_applications_job_id", "job_id"),
        Index("ix_job_applications_status", "status"),
        Index("ix_job_applications_candidate_status", "candidate_id", "status"),
    )

    # --- Foreign Keys ---
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Resume that was attached when applying (nullable — may be set later)
    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tailored_resumes.id", ondelete="SET NULL"),
        nullable=True,
    )

    # --- Lifecycle State ---
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, native_enum=False, length=50),
        default=ApplicationStatus.DISCOVERED,
        nullable=False,
    )

    # --- Application Details ---
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    external_job_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    external_application_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Cover letter / custom message drafted for this application
    cover_letter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Form Field Mapping (APP-001) ---
    # JSON snapshot of the form fields detected on the application page
    detected_form_fields: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    # Mapped form field values (field_name → value) ready to submit
    mapped_field_values: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    # --- Automation Metadata (APP-002) ---
    # Automation level determined at time of submission attempt
    automation_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Number of human handoff events during this application
    handoff_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # --- Notes & Audit ---
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # History of status transitions: [{action, from, to, timestamp, actor}]
    transition_history: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=list, nullable=False
    )

    # --- Relationships ---
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile")
    job: Mapped[Optional["Job"]] = relationship("Job")
    resume: Mapped[Optional["TailoredResume"]] = relationship("TailoredResume")
