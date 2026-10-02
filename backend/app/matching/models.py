"""SQLAlchemy database models for Candidate-Job Matches and scoring logs."""

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
    Index,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.matching.enums import MatchStatus


class JobMatch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Stores the calculated match score, breakdown, and gap analysis between a Candidate and a Job."""

    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_candidate_job_match"),
        Index("ix_job_matches_candidate_score", "candidate_id", "overall_score"),
        Index("ix_job_matches_status", "status"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    search_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_search_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Scores (0.0 to 100.0)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    skill_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    role_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    experience_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    location_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    vector_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status & Hard Filter evaluation
    status: Mapped[MatchStatus] = mapped_column(
        SQLEnum(MatchStatus, native_enum=False, length=50),
        default=MatchStatus.MODERATE_MATCH,
        nullable=False
    )
    passed_hard_filters: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    filter_rejection_reasons: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    # Detailed Skill & Gap Analysis
    matched_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    missing_mandatory_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    missing_preferred_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    # Explainability & Insights
    highlights: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    concerns: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    reasoning_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # User Interactions
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile")
    job: Mapped["Job"] = relationship("Job")
    search_profile: Mapped[Optional["CareerSearchProfile"]] = relationship("CareerSearchProfile")
