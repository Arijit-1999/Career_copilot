"""SQLAlchemy ORM models for the tracking and analytics domain."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    String,
    Text,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    Index,
    Integer,
    Float,
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.applications.enums import ApplicationStatus
from app.tracking.enums import (
    TimelineEventType,
    InterviewRoundType,
    InterviewFormat,
    InterviewOutcome,
    RejectionCategory,
    OfferOutcome,
)


class ApplicationTimelineEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Logs chronological milestone events, status transitions, and notes for an application."""

    __tablename__ = "application_timeline_events"
    __table_args__ = (
        Index("ix_timeline_app_id", "application_id"),
        Index("ix_timeline_event_type", "event_type"),
        Index("ix_timeline_event_timestamp", "event_timestamp"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[TimelineEventType] = mapped_column(
        SQLEnum(TimelineEventType, native_enum=False, length=50),
        nullable=False,
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    extra_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    application = relationship("JobApplication", backref="timeline_events")


class ApplicationInterview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks interview stages, schedules, interviewer details, and debrief notes."""

    __tablename__ = "application_interviews"
    __table_args__ = (
        Index("ix_interviews_app_id", "application_id"),
        Index("ix_interviews_scheduled_at", "scheduled_at"),
        Index("ix_interviews_outcome", "outcome"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
    )
    round_type: Mapped[InterviewRoundType] = mapped_column(
        SQLEnum(InterviewRoundType, native_enum=False, length=50),
        default=InterviewRoundType.RECRUITER_SCREEN,
        nullable=False,
    )
    round_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    format: Mapped[InterviewFormat] = mapped_column(
        SQLEnum(InterviewFormat, native_enum=False, length=50),
        default=InterviewFormat.VIDEO_CALL,
        nullable=False,
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    interviewer_names: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    interviewer_titles: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    meeting_link: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preparation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    questions_asked: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback_received: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outcome: Mapped[InterviewOutcome] = mapped_column(
        SQLEnum(InterviewOutcome, native_enum=False, length=50),
        default=InterviewOutcome.SCHEDULED,
        nullable=False,
    )

    # Relationships
    application = relationship("JobApplication", backref="interviews")


class ApplicationOutcome(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Stores the terminal resolution, compensation packages, rejection breakdown, and learnings."""

    __tablename__ = "application_outcomes"
    __table_args__ = (
        Index("ix_outcomes_app_id", "application_id", unique=True),
        Index("ix_outcomes_final_status", "final_status"),
        Index("ix_outcomes_rejection_cat", "rejection_category"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    final_status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, native_enum=False, length=50),
        nullable=False,
    )
    rejection_category: Mapped[Optional[RejectionCategory]] = mapped_column(
        SQLEnum(RejectionCategory, native_enum=False, length=50),
        nullable=True,
    )
    rejection_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    offer_outcome: Mapped[Optional[OfferOutcome]] = mapped_column(
        SQLEnum(OfferOutcome, native_enum=False, length=50),
        nullable=True,
    )
    offer_salary_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    offer_salary_currency: Mapped[Optional[str]] = mapped_column(String(10), default="INR", nullable=True)
    offer_equity: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    offer_bonus: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    offer_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    lessons_learned: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_time_days: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    application = relationship("JobApplication", backref="outcome", uselist=False)
