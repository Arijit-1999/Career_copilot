"""Pydantic schemas for structured JD understanding and requirement extraction."""

import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from app.extraction.enums import (
    SeniorityLevel,
    RequirementCategory,
    RequirementImportance
)


class ExtractedRequirement(BaseModel):
    """An individual structured requirement extracted from a job description."""
    skill_name: str
    canonical_name: str
    category: RequirementCategory
    importance: RequirementImportance
    min_years: Optional[float] = None
    context_snippet: Optional[str] = None


class JobUnderstandingResult(BaseModel):
    """Full structured extraction result from a job description."""
    seniority: SeniorityLevel
    min_experience_years: Optional[float] = None
    max_experience_years: Optional[float] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    extracted_tags: List[str] = Field(default_factory=list)
    requirements: List[ExtractedRequirement] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    education_requirements: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class JDAnalysisRequest(BaseModel):
    """Request payload for stateless JD extraction and analysis."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)
    company: Optional[str] = None


class JDAnalysisResponse(BaseModel):
    """Response payload for stateless JD extraction."""
    title: str
    company: Optional[str] = None
    result: JobUnderstandingResult


class JobExtractAndPersistResponse(BaseModel):
    """Response returned when extracting requirements and updating an existing Job record."""
    job_id: uuid.UUID
    result: JobUnderstandingResult
    updated_at: str
