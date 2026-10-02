"""Service layer for career search profiles."""

import uuid
from typing import List, Optional, Sequence
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.career_profiles.models import CareerSearchProfile
from app.career_profiles.schemas import (
    CareerSearchProfileCreate,
    CareerSearchProfileUpdate,
    IntentExpansionRequest,
    IntentExpansionResponse
)
from app.career_profiles.intent_agent import CareerIntentAgent
from app.core.exceptions import EntityNotFoundException


class CareerProfileService:
    """Service managing candidate search profiles and role expansion."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_search_profile(
        self, candidate_id: uuid.UUID, profile_in: CareerSearchProfileCreate
    ) -> CareerSearchProfile:
        """Creates a new search profile for a candidate."""
        # Convert work_modes enums to strings for storage
        work_modes_str = [wm.value if hasattr(wm, "value") else str(wm) for wm in profile_in.work_modes]

        profile = CareerSearchProfile(
            candidate_id=candidate_id,
            name=profile_in.name,
            target_roles=profile_in.target_roles,
            alternative_roles=profile_in.alternative_roles,
            required_skills=profile_in.required_skills,
            preferred_skills=profile_in.preferred_skills,
            excluded_skills=profile_in.excluded_skills,
            locations=profile_in.locations,
            work_modes=work_modes_str,
            min_experience_years=profile_in.min_experience_years,
            max_experience_years=profile_in.max_experience_years,
            min_salary=profile_in.min_salary,
            target_salary=profile_in.target_salary,
            currency=profile_in.currency,
            is_active=profile_in.is_active,
            intent_query=profile_in.intent_query
        )
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def list_search_profiles(
        self, candidate_id: uuid.UUID, active_only: bool = False
    ) -> Sequence[CareerSearchProfile]:
        """Lists search profiles for a candidate."""
        query = (
            select(CareerSearchProfile)
            .where(CareerSearchProfile.candidate_id == candidate_id)
            .order_by(CareerSearchProfile.created_at.desc())
        )
        if active_only:
            query = query.where(CareerSearchProfile.is_active == True)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_search_profile_by_id(
        self, candidate_id: uuid.UUID, profile_id: uuid.UUID
    ) -> CareerSearchProfile:
        """Retrieves a specific search profile."""
        query = select(CareerSearchProfile).where(
            CareerSearchProfile.id == profile_id,
            CareerSearchProfile.candidate_id == candidate_id
        )
        result = await self.db.execute(query)
        profile = result.scalar_one_or_none()
        if not profile:
            raise EntityNotFoundException(f"Search profile {profile_id} not found")
        return profile

    async def update_search_profile(
        self, candidate_id: uuid.UUID, profile_id: uuid.UUID, update_in: CareerSearchProfileUpdate
    ) -> CareerSearchProfile:
        """Updates search profile details."""
        profile = await self.get_search_profile_by_id(candidate_id, profile_id)
        update_data = update_in.model_dump(exclude_unset=True)

        if "work_modes" in update_data and update_data["work_modes"] is not None:
            update_data["work_modes"] = [
                wm.value if hasattr(wm, "value") else str(wm) for wm in update_data["work_modes"]
            ]

        for field, value in update_data.items():
            setattr(profile, field, value)

        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def delete_search_profile(
        self, candidate_id: uuid.UUID, profile_id: uuid.UUID
    ) -> bool:
        """Deletes a search profile."""
        profile = await self.get_search_profile_by_id(candidate_id, profile_id)
        await self.db.delete(profile)
        await self.db.commit()
        return True

    @staticmethod
    def expand_career_intent(request: IntentExpansionRequest) -> IntentExpansionResponse:
        """Runs the deterministic career intent agent to suggest related roles."""
        return CareerIntentAgent.expand_intent(request.query)
