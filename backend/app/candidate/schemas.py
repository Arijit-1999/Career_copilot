"""Pydantic request and response schemas for candidate intelligence."""

import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.candidate.enums import (
    SkillState,
    FactType,
    FactVerificationStatus,
    WorkModePreference
)


# ==========================================
# Skill Schemas
# ==========================================

class SkillBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    category: Optional[str] = Field(None, max_length=100)


class SkillCreate(SkillBase):
    pass


class SkillResponse(SkillBase):
    id: uuid.UUID
    canonical_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateSkillCreate(BaseModel):
    skill_name: str = Field(..., min_length=1, max_length=150)
    category: Optional[str] = None
    state: SkillState = SkillState.CLAIMED
    years_experience: Optional[float] = Field(0.0, ge=0.0)
    confidence_level: int = Field(3, ge=1, le=5)
    evidence_notes: Optional[str] = None


class CandidateSkillUpdate(BaseModel):
    state: Optional[SkillState] = None
    years_experience: Optional[float] = Field(None, ge=0.0)
    confidence_level: Optional[int] = Field(None, ge=1, le=5)
    evidence_notes: Optional[str] = None


class CandidateSkillResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    skill_id: uuid.UUID
    skill_name: Optional[str] = ""
    category: Optional[str] = None
    state: SkillState
    years_experience: Optional[float] = 0.0
    confidence_level: int = 3
    evidence_notes: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Resume Fact Schemas
# ==========================================

class ResumeFactCreate(BaseModel):
    fact_type: FactType
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    source_reference: Optional[str] = None
    verification_status: FactVerificationStatus = FactVerificationStatus.UNVERIFIED
    tags: List[str] = Field(default_factory=list)


class ResumeFactUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    source_reference: Optional[str] = None
    verification_status: Optional[FactVerificationStatus] = None
    tags: Optional[List[str]] = None


class ResumeFactResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    fact_type: FactType
    title: str
    description: str
    metrics: Dict[str, Any]
    source_reference: Optional[str]
    verification_status: FactVerificationStatus
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Experience & Project Schemas
# ==========================================

class ExperienceCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    is_current: bool = False
    description: Optional[str] = None


class ExperienceResponse(ExperienceCreate):
    id: uuid.UUID
    candidate_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = None
    description: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    repo_url: Optional[str] = None


class ProjectResponse(ProjectCreate):
    id: uuid.UUID
    candidate_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Candidate Profile Schemas
# ==========================================

class CandidateProfileCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None
    current_title: Optional[str] = None
    summary: Optional[str] = None
    target_roles: List[str] = Field(default_factory=list)
    work_mode: WorkModePreference = WorkModePreference.FLEXIBLE
    min_salary: Optional[float] = None
    target_salary: Optional[float] = None
    currency: str = Field("INR", max_length=10)


class CandidateProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    current_title: Optional[str] = None
    summary: Optional[str] = None
    target_roles: Optional[List[str]] = None
    work_mode: Optional[WorkModePreference] = None
    min_salary: Optional[float] = None
    target_salary: Optional[float] = None
    currency: Optional[str] = None


class CandidateProfileResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    phone: Optional[str]
    location: Optional[str]
    current_title: Optional[str]
    summary: Optional[str]
    target_roles: List[str]
    work_mode: WorkModePreference
    min_salary: Optional[float]
    target_salary: Optional[float]
    currency: str
    created_at: datetime
    updated_at: datetime
    skills: List[CandidateSkillResponse] = Field(default_factory=list)
    facts: List[ResumeFactResponse] = Field(default_factory=list)
    experiences: List[ExperienceResponse] = Field(default_factory=list)
    projects: List[ProjectResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
