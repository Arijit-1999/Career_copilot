"""Pydantic request and response schemas for job ingestion and queries."""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.candidate.enums import WorkModePreference
from app.jobs.enums import JobSourceType, JobFreshness, JobStatus


class JobIngestRequest(BaseModel):
    """Raw job ingestion payload from scraper, adapter, or candidate."""
    title: str = Field(..., min_length=1, max_length=255)
    company: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=5)
    source: JobSourceType = JobSourceType.MANUAL
    source_job_id: Optional[str] = None
    application_url: Optional[str] = None
    location: Optional[str] = "Remote"
    work_mode: Optional[WorkModePreference] = None
    employment_type: Optional[str] = "Full-time"
    salary_raw: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = "INR"
    min_experience_years: Optional[float] = None
    max_experience_years: Optional[float] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    posted_at: Optional[datetime] = None


class JobResponse(BaseModel):
    """Normalized canonical job response."""
    id: uuid.UUID
    source: JobSourceType
    source_job_id: Optional[str] = None
    application_url: Optional[str] = None
    canonical_url: Optional[str] = None
    title: str
    normalized_title: str
    company: str
    location: str
    work_mode: WorkModePreference
    employment_type: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: str
    salary_raw: Optional[str] = None
    min_experience_years: Optional[float] = None
    max_experience_years: Optional[float] = None
    description_clean: str
    content_hash: str
    required_skills: List[str]
    preferred_skills: List[str]
    extracted_tags: List[str]
    posted_at: Optional[datetime] = None
    first_seen_at: datetime
    last_seen_at: datetime
    freshness: JobFreshness
    status: JobStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobIngestResult(BaseModel):
    """Result of single job ingestion."""
    job: JobResponse
    is_duplicate: bool
    action: str  # "created" or "seen_again"


class JobBatchIngestRequest(BaseModel):
    """Batch ingestion request."""
    jobs: List[JobIngestRequest] = Field(..., min_length=1)


class JobBatchIngestResponse(BaseModel):
    """Batch ingestion summary metrics."""
    total_received: int
    new_jobs_added: int
    duplicates_seen: int
    results: List[JobIngestResult]
