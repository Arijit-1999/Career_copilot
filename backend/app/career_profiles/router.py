"""REST API router for multi-target search profiles and career intent expansion."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.candidate.service import CandidateService
from app.candidate.schemas import CandidateProfileCreate
from app.career_profiles.service import CareerProfileService
from app.career_profiles.schemas import (
    CareerSearchProfileCreate,
    CareerSearchProfileUpdate,
    CareerSearchProfileResponse,
    IntentExpansionRequest,
    IntentExpansionResponse
)

router = APIRouter(tags=["Career Profiles"])


def get_services(db: AsyncSession = Depends(get_db_session)):
    return {
        "candidate": CandidateService(db),
        "search": CareerProfileService(db)
    }


async def get_or_create_active_candidate_id(candidate_service: CandidateService) -> uuid.UUID:
    """Helper to ensure active candidate profile exists."""
    active = await candidate_service.get_active_profile()
    if not active:
        active = await candidate_service.get_or_create_profile(
            CandidateProfileCreate(full_name="Active Candidate", email="candidate@example.com")
        )
    return active.id


# =========================================================
# Intent Expansion Endpoints (MUST be before /{profile_id})
# =========================================================

@router.post("/expand-intent", response_model=IntentExpansionResponse)
async def expand_career_intent(
    request: IntentExpansionRequest,
    services: dict = Depends(get_services)
):
    """Analyzes a natural language career goal to expand it into target and alternative roles."""
    return services["search"].expand_career_intent(request)


@router.get("/expand-intent", response_model=IntentExpansionResponse)
async def expand_career_intent_get(
    query: str = Query("Python backend and AWS data engineering roles", description="Natural language career goal"),
    services: dict = Depends(get_services)
):
    """GET convenience endpoint to expand career intent via query parameter."""
    req = IntentExpansionRequest(query=query)
    return services["search"].expand_career_intent(req)


# =========================================================
# Search Profile Collections
# =========================================================

@router.post("", response_model=CareerSearchProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_search_profile(
    profile_in: CareerSearchProfileCreate,
    services: dict = Depends(get_services)
):
    """Creates a new target search profile."""
    candidate_id = await get_or_create_active_candidate_id(services["candidate"])
    return await services["search"].create_search_profile(candidate_id, profile_in)


@router.get("", response_model=List[CareerSearchProfileResponse])
async def list_search_profiles(
    active_only: bool = Query(False, description="Filter for only active profiles"),
    services: dict = Depends(get_services)
):
    """Lists all search profiles configured for the candidate."""
    candidate_id = await get_or_create_active_candidate_id(services["candidate"])
    return await services["search"].list_search_profiles(candidate_id, active_only=active_only)


# =========================================================
# Single Profile by UUID Operations
# =========================================================

@router.get("/{profile_id}", response_model=CareerSearchProfileResponse)
async def get_search_profile(
    profile_id: uuid.UUID,
    services: dict = Depends(get_services)
):
    """Retrieves a search profile by ID."""
    candidate_id = await get_or_create_active_candidate_id(services["candidate"])
    return await services["search"].get_search_profile_by_id(candidate_id, profile_id)


@router.put("/{profile_id}", response_model=CareerSearchProfileResponse)
async def update_search_profile(
    profile_id: uuid.UUID,
    update_in: CareerSearchProfileUpdate,
    services: dict = Depends(get_services)
):
    """Updates a search profile."""
    candidate_id = await get_or_create_active_candidate_id(services["candidate"])
    return await services["search"].update_search_profile(candidate_id, profile_id, update_in)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search_profile(
    profile_id: uuid.UUID,
    services: dict = Depends(get_services)
):
    """Deletes a search profile."""
    candidate_id = await get_or_create_active_candidate_id(services["candidate"])
    await services["search"].delete_search_profile(candidate_id, profile_id)
    return None
