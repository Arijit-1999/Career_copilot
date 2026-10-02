"""Pydantic schemas for search profiles and career intent expansion."""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.candidate.enums import WorkModePreference


class CareerSearchProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    target_roles: List[str] = Field(..., min_length=1)
    alternative_roles: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    excluded_skills: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    work_modes: List[WorkModePreference] = Field(default_factory=list)
    min_experience_years: Optional[float] = Field(0.0, ge=0.0)
    max_experience_years: Optional[float] = Field(None, ge=0.0)
    min_salary: Optional[float] = None
    target_salary: Optional[float] = None
    currency: str = Field("INR", max_length=10)
    is_active: bool = True
    intent_query: Optional[str] = None


class CareerSearchProfileUpdate(BaseModel):
    name: Optional[str] = None
    target_roles: Optional[List[str]] = None
    alternative_roles: Optional[List[str]] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    excluded_skills: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    work_modes: Optional[List[WorkModePreference]] = None
    min_experience_years: Optional[float] = Field(None, ge=0.0)
    max_experience_years: Optional[float] = Field(None, ge=0.0)
    min_salary: Optional[float] = None
    target_salary: Optional[float] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


class CareerSearchProfileResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    name: str
    target_roles: List[str]
    alternative_roles: List[str]
    required_skills: List[str]
    preferred_skills: List[str]
    excluded_skills: List[str]
    locations: List[str]
    work_modes: List[str]
    min_experience_years: Optional[float]
    max_experience_years: Optional[float]
    min_salary: Optional[float]
    target_salary: Optional[float]
    currency: str
    is_active: bool
    intent_query: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Career Intent Expansion DTOs
# ==========================================

class IntentExpansionRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500, description="Natural-language career goal or skills description")


class SuggestedRoleDetail(BaseModel):
    role_title: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    primary_skills: List[str]
    rationale: str


class IntentExpansionResponse(BaseModel):
    original_query: str
    primary_roles: List[str]
    alternative_roles: List[str]
    recommended_skills: List[str]
    role_details: List[SuggestedRoleDetail]
    expansion_method: str = "deterministic_ontology"
