"""SQLAlchemy database models for multi-target search profiles."""

import uuid
from typing import List, Optional
from sqlalchemy import (
    String,
    Text,
    Float,
    Boolean,
    ForeignKey,
    JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CareerSearchProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a targeted search profile configured by the candidate."""

    __tablename__ = "career_search_profiles"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Target Roles
    target_roles: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    alternative_roles: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    # Skill Requirements
    required_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    excluded_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    # Location & Work Mode Preferences
    locations: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    work_modes: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    
    # Experience & Compensation
    min_experience_years: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)
    max_experience_years: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    
    # Control Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    intent_query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship back to candidate
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile")
