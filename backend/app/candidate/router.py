"""Candidate domain REST API router."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.candidate.service import CandidateService
from app.candidate.enums import SkillState, FactType, FactVerificationStatus
from app.candidate.schemas import (
    CandidateProfileCreate,
    CandidateProfileUpdate,
    CandidateProfileResponse,
    CandidateSkillCreate,
    CandidateSkillResponse,
    ResumeFactCreate,
    ResumeFactResponse,
    ExperienceCreate,
    ExperienceResponse,
    ProjectCreate,
    ProjectResponse
)

router = APIRouter(tags=["Candidate"])


def get_candidate_service(db: AsyncSession = Depends(get_db_session)) -> CandidateService:
    return CandidateService(db)


@router.post("", response_model=CandidateProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_in: CandidateProfileCreate,
    service: CandidateService = Depends(get_candidate_service)
):
    """Creates or initializes candidate profile."""
    profile = await service.get_or_create_profile(profile_in)
    return profile


@router.get("/me", response_model=CandidateProfileResponse)
async def get_active_profile(
    service: CandidateService = Depends(get_candidate_service)
):
    """Retrieves the active candidate profile."""
    profile = await service.get_active_profile()
    if not profile:
        # Return default initialized structure if no profile exists yet
        default_in = CandidateProfileCreate(
            full_name="Default Candidate",
            email="candidate@example.com",
            current_title="Software Engineer"
        )
        profile = await service.get_or_create_profile(default_in)
    return profile


@router.put("/me", response_model=CandidateProfileResponse)
async def update_profile(
    update_in: CandidateProfileUpdate,
    service: CandidateService = Depends(get_candidate_service)
):
    """Updates the active candidate profile."""
    active = await service.get_active_profile()
    if not active:
        active = await service.get_or_create_profile(
            CandidateProfileCreate(full_name="Candidate", email="candidate@example.com")
        )
    return await service.update_profile(active.id, update_in)


# ==========================================
# Skills Endpoints
# ==========================================

@router.post("/skills", status_code=status.HTTP_201_CREATED)
async def add_or_update_skill(
    skill_in: CandidateSkillCreate,
    service: CandidateService = Depends(get_candidate_service)
):
    """Adds or updates a candidate skill with state machine enforcement."""
    active = await service.get_active_profile()
    if not active:
        active = await service.get_or_create_profile(
            CandidateProfileCreate(full_name="Candidate", email="candidate@example.com")
        )
    cand_skill = await service.add_or_update_candidate_skill(active.id, skill_in)
    return {
        "id": cand_skill.id,
        "candidate_id": cand_skill.candidate_id,
        "skill_id": cand_skill.skill_id,
        "skill_name": skill_in.skill_name,
        "category": skill_in.category,
        "state": cand_skill.state,
        "years_experience": cand_skill.years_experience,
        "confidence_level": cand_skill.confidence_level,
        "evidence_notes": cand_skill.evidence_notes,
        "verified_at": cand_skill.verified_at,
        "created_at": cand_skill.created_at,
        "updated_at": cand_skill.updated_at
    }


@router.get("/skills")
async def list_candidate_skills(
    state: Optional[SkillState] = Query(None, description="Filter by skill state (e.g. VERIFIED, LEARNING)"),
    service: CandidateService = Depends(get_candidate_service)
):
    """Lists candidate skills, optionally filtered by state."""
    active = await service.get_active_profile()
    if not active:
        return []
    skills = await service.list_candidate_skills(active.id, state=state)
    return [
        {
            "id": s.id,
            "candidate_id": s.candidate_id,
            "skill_id": s.skill_id,
            "skill_name": s.skill.name if s.skill else "",
            "category": s.skill.category if s.skill else None,
            "state": s.state,
            "years_experience": s.years_experience,
            "confidence_level": s.confidence_level,
            "evidence_notes": s.evidence_notes,
            "verified_at": s.verified_at,
            "created_at": s.created_at,
            "updated_at": s.updated_at
        }
        for s in skills
    ]


# ==========================================
# Resume Fact Bank Endpoints
# ==========================================

@router.post("/facts", response_model=ResumeFactResponse, status_code=status.HTTP_201_CREATED)
async def add_resume_fact(
    fact_in: ResumeFactCreate,
    service: CandidateService = Depends(get_candidate_service)
):
    """Adds a structured fact to the Resume Fact Bank."""
    active = await service.get_active_profile()
    if not active:
        active = await service.get_or_create_profile(
            CandidateProfileCreate(full_name="Candidate", email="candidate@example.com")
        )
    return await service.add_resume_fact(active.id, fact_in)


@router.get("/facts", response_model=List[ResumeFactResponse])
async def list_resume_facts(
    fact_type: Optional[FactType] = Query(None, description="Filter by fact type"),
    verification_status: Optional[FactVerificationStatus] = Query(None, description="Filter by status (e.g. VERIFIED)"),
    service: CandidateService = Depends(get_candidate_service)
):
    """Queries facts from the Resume Fact Bank."""
    active = await service.get_active_profile()
    if not active:
        return []
    return await service.list_resume_facts(
        active.id, fact_type=fact_type, verification_status=verification_status
    )


# ==========================================
# Experiences & Projects Endpoints
# ==========================================

@router.post("/experiences", response_model=ExperienceResponse, status_code=status.HTTP_201_CREATED)
async def add_experience(
    exp_in: ExperienceCreate,
    service: CandidateService = Depends(get_candidate_service)
):
    """Adds an employment experience record."""
    active = await service.get_active_profile()
    if not active:
        active = await service.get_or_create_profile(
            CandidateProfileCreate(full_name="Candidate", email="candidate@example.com")
        )
    return await service.add_experience(active.id, exp_in)


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def add_project(
    proj_in: ProjectCreate,
    service: CandidateService = Depends(get_candidate_service)
):
    """Adds a portfolio project record."""
    active = await service.get_active_profile()
    if not active:
        active = await service.get_or_create_profile(
            CandidateProfileCreate(full_name="Candidate", email="candidate@example.com")
        )
    return await service.add_project(active.id, proj_in)
