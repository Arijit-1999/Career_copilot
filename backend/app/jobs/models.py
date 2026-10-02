"""SQLAlchemy database models for normalized jobs and sources."""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    String,
    Text,
    Float,
    DateTime,
    Enum as SQLEnum,
    JSON,
    Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.candidate.enums import WorkModePreference
from app.jobs.enums import JobSourceType, JobFreshness, JobStatus


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Primary normalized job representation across all platforms."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_source_source_id", "source", "source_job_id"),
        Index("ix_jobs_content_hash", "content_hash"),
        Index("ix_jobs_canonical_url", "canonical_url"),
        Index("ix_jobs_company_title", "company", "normalized_title"),
    )

    # Source provenance
    source: Mapped[JobSourceType] = mapped_column(
        SQLEnum(JobSourceType, native_enum=False, length=50),
        default=JobSourceType.MANUAL,
        nullable=False,
        index=True
    )
    source_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    application_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Core Job Details
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), default="Remote", nullable=False)
    work_mode: Mapped[WorkModePreference] = mapped_column(
        SQLEnum(WorkModePreference, native_enum=False, length=50),
        default=WorkModePreference.FLEXIBLE,
        nullable=False,
        index=True
    )
    employment_type: Mapped[str] = mapped_column(String(50), default="Full-time", nullable=False)

    # Compensation
    salary_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    salary_raw: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Experience Requirements
    min_experience_years: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)
    max_experience_years: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Description & Content
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    description_clean: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Skills & Requirements (Extracted/Provided)
    required_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    extracted_tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    # Freshness & Tracking Timestamps
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    freshness: Mapped[JobFreshness] = mapped_column(
        SQLEnum(JobFreshness, native_enum=False, length=50),
        default=JobFreshness.VERY_FRESH,
        nullable=False,
        index=True
    )
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, native_enum=False, length=50),
        default=JobStatus.DISCOVERED,
        nullable=False,
        index=True
    )
