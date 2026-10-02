"""Pydantic schemas and DTOs for matching engine and match reports."""

import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from app.candidate.enums import SkillState, WorkModePreference
from app.matching.enums import MatchStatus, FilterRejectionReason


class SkillMatchItem(BaseModel):
    """Details on a single skill evaluated against the job."""
    skill_name: str
    is_mandatory: bool
    is_matched: bool
    candidate_state: Optional[SkillState] = None
    weight_credit: float = Field(default=0.0, ge=0.0, le=1.0)


class MatchScoreBreakdown(BaseModel):
    """Full quantitative and qualitative scoring breakdown."""
    overall_score: float = Field(..., ge=0.0, le=100.0)
    skill_score: float = Field(..., ge=0.0, le=100.0)
    role_score: float = Field(..., ge=0.0, le=100.0)
    experience_score: float = Field(..., ge=0.0, le=100.0)
    location_score: float = Field(..., ge=0.0, le=100.0)
    vector_score: Optional[float] = None
    
    # Filter status
    passed_hard_filters: bool
    rejection_reasons: List[FilterRejectionReason] = Field(default_factory=list)

    # Gaps & matches
    matched_skills: List[str] = Field(default_factory=list)
    missing_mandatory_skills: List[str] = Field(default_factory=list)
    missing_preferred_skills: List[str] = Field(default_factory=list)
    skill_details: List[SkillMatchItem] = Field(default_factory=list)

    # Explainable Highlights & Concerns
    highlights: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    reasoning_summary: Optional[str] = None


class MatchJobRequest(BaseModel):
    """Request to evaluate a single job against candidate / target profile."""
    candidate_id: Optional[uuid.UUID] = None
    job_id: uuid.UUID
    search_profile_id: Optional[uuid.UUID] = None
    strict_filters: bool = True


class MatchJobResponse(BaseModel):
    """Response returned after evaluating a single job match."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[uuid.UUID] = None
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    search_profile_id: Optional[uuid.UUID] = None
    job_title: str
    company: str
    location: str
    work_mode: str
    overall_score: float
    status: MatchStatus
    breakdown: MatchScoreBreakdown


class BatchMatchRequest(BaseModel):
    """Request to batch match all active jobs against a candidate / search profile."""
    candidate_id: Optional[uuid.UUID] = None
    search_profile_id: Optional[uuid.UUID] = None
    min_score: float = Field(default=40.0, ge=0.0, le=100.0)
    limit: int = Field(default=50, ge=1, le=200)
    only_passed_filters: bool = True


class JobMatchSummary(BaseModel):
    """Summary item in top matches feed."""
    model_config = ConfigDict(from_attributes=True)

    match_id: uuid.UUID
    job_id: uuid.UUID
    job_title: str
    company: str
    location: str
    work_mode: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    overall_score: float
    skill_score: float
    status: MatchStatus
    passed_hard_filters: bool
    matched_skills: List[str] = Field(default_factory=list)
    missing_mandatory_skills: List[str] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)
    is_starred: bool = False
    is_applied: bool = False
    created_at: str


class BatchMatchResponse(BaseModel):
    """Result of batch matching evaluation."""
    candidate_id: uuid.UUID
    total_jobs_evaluated: int
    qualified_matches_count: int
    matches: List[JobMatchSummary] = Field(default_factory=list)
