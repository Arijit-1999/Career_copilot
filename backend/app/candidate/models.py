"""SQLAlchemy database models for candidate intelligence, skills, and fact bank."""

import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.candidate.enums import (
    SkillState,
    FactType,
    FactVerificationStatus,
    WorkModePreference
)


class CandidateProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Primary candidate profile model."""

    __tablename__ = "candidate_profiles"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Preferences
    target_roles: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    work_mode: Mapped[WorkModePreference] = mapped_column(
        SQLEnum(WorkModePreference, native_enum=False, length=50),
        default=WorkModePreference.FLEXIBLE,
        nullable=False
    )
    min_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)

    # Relationships
    skills: Mapped[List["CandidateSkill"]] = relationship(
        "CandidateSkill",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    facts: Mapped[List["ResumeFact"]] = relationship(
        "ResumeFact",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    experiences: Mapped[List["CandidateExperience"]] = relationship(
        "CandidateExperience",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    projects: Mapped[List["CandidateProject"]] = relationship(
        "CandidateProject",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class Skill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Global canonical skill dictionary."""

    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., Languages, Cloud, Frameworks


class CandidateSkill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Associates a candidate with a skill, enforcing state tracking and provenance."""

    __tablename__ = "candidate_skills"
    __table_args__ = (
        UniqueConstraint("candidate_id", "skill_id", name="uq_candidate_skill"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    state: Mapped[SkillState] = mapped_column(
        SQLEnum(SkillState, native_enum=False, length=50),
        default=SkillState.CLAIMED,
        nullable=False,
        index=True
    )
    years_experience: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)
    confidence_level: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 1 to 5
    evidence_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="skills")
    skill: Mapped["Skill"] = relationship("Skill", lazy="joined")

    @property
    def skill_name(self) -> str:
        return self.skill.name if self.skill else ""

    @property
    def category(self) -> Optional[str]:
        return self.skill.category if self.skill else None


class ResumeFact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Atomic verifiable fact unit in the candidate's Resume Fact Bank."""

    __tablename__ = "resume_facts"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    fact_type: Mapped[FactType] = mapped_column(
        SQLEnum(FactType, native_enum=False, length=50),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verification_status: Mapped[FactVerificationStatus] = mapped_column(
        SQLEnum(FactVerificationStatus, native_enum=False, length=50),
        default=FactVerificationStatus.UNVERIFIED,
        nullable=False,
        index=True
    )
    tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="facts")


class CandidateExperience(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Candidate work experience entry."""

    __tablename__ = "candidate_experiences"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="experiences")


class CandidateProject(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Candidate project entry."""

    __tablename__ = "candidate_projects"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tech_stack: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    repo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="projects")
