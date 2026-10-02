"""Pydantic schemas and DTOs for Resume tailoring, structured content, and truth validation."""

import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from app.resumes.enums import ResumeStatus, ResumeFormat, ValidationSeverity


class ResumeSectionHeader(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    title: Optional[str] = None


class ResumeSkillGroup(BaseModel):
    category_name: str
    skills: List[str] = Field(default_factory=list)


class ResumeExperienceItem(BaseModel):
    company: str
    title: str
    location: Optional[str] = None
    start_date: str
    end_date: str
    is_current: bool = False
    bullets: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)


class ResumeProjectItem(BaseModel):
    name: str
    role: Optional[str] = None
    description: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    url: Optional[str] = None


class ResumeStructuredContent(BaseModel):
    header: ResumeSectionHeader
    summary: str
    skill_groups: List[ResumeSkillGroup] = Field(default_factory=list)
    experiences: List[ResumeExperienceItem] = Field(default_factory=list)
    projects: List[ResumeProjectItem] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)


class TruthValidationClaim(BaseModel):
    claim_text: str
    severity: ValidationSeverity
    is_verified: bool
    source_reference: Optional[str] = None
    explanation: str


class TruthValidationResult(BaseModel):
    is_valid: bool
    truth_score: float = Field(default=100.0, ge=0.0, le=100.0)
    verified_claims_count: int = 0
    unverified_claims_count: int = 0
    claims: List[TruthValidationClaim] = Field(default_factory=list)
    hallucinations_detected: List[str] = Field(default_factory=list)


class GenerateTailoredResumeRequest(BaseModel):
    candidate_id: Optional[uuid.UUID] = None
    job_id: uuid.UUID
    target_role: Optional[str] = None
    max_bullets_per_experience: int = Field(default=4, ge=2, le=6)
    include_claimed_skills: bool = False  # If false, strictly only VERIFIED skills are included


class GenerateMasterResumeRequest(BaseModel):
    candidate_id: Optional[uuid.UUID] = None
    title: Optional[str] = "Master Technical Resume"


class TailoredResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    title: str
    target_role: Optional[str] = None
    is_master: bool
    status: ResumeStatus
    raw_markdown: str
    structured_content: Dict[str, Any]
    targeted_skills: List[str] = Field(default_factory=list)
    truth_score: float
    validation_report: Dict[str, Any] = Field(default_factory=dict)
    user_notes: Optional[str] = None
    created_at: str
    updated_at: str


class TailoredResumeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    title: str
    is_master: bool
    status: ResumeStatus
    truth_score: float
    targeted_skills: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class ResumeUpdateRequest(BaseModel):
    raw_markdown: Optional[str] = None
    status: Optional[ResumeStatus] = None
    user_notes: Optional[str] = None


class ValidateResumeTextRequest(BaseModel):
    candidate_id: Optional[uuid.UUID] = None
    resume_text: str
