"""Business service layer for candidate profile, skills, and resume fact bank."""

import uuid
from typing import List, Optional, Sequence
from datetime import datetime, timezone

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.candidate.models import (
    CandidateProfile,
    Skill,
    CandidateSkill,
    ResumeFact,
    CandidateExperience,
    CandidateProject
)
from app.candidate.enums import SkillState, FactVerificationStatus, FactType
from app.candidate.schemas import (
    CandidateProfileCreate,
    CandidateProfileUpdate,
    CandidateSkillCreate,
    CandidateSkillUpdate,
    ResumeFactCreate,
    ResumeFactUpdate,
    ExperienceCreate,
    ProjectCreate
)
from app.core.exceptions import EntityNotFoundException, DuplicateEntityException
from app.common.models import utc_now


class CandidateService:
    """Service managing candidate intelligence and fact bank operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_profile(self, profile_in: CandidateProfileCreate) -> CandidateProfile:
        """Retrieves an existing profile by email or creates a new one."""
        query = select(CandidateProfile).where(CandidateProfile.email == profile_in.email)
        result = await self.db.execute(query)
        profile = result.scalar_one_or_none()

        if profile:
            return profile

        profile = CandidateProfile(
            full_name=profile_in.full_name,
            email=profile_in.email,
            phone=profile_in.phone,
            location=profile_in.location,
            current_title=profile_in.current_title,
            summary=profile_in.summary,
            target_roles=profile_in.target_roles,
            work_mode=profile_in.work_mode,
            min_salary=profile_in.min_salary,
            target_salary=profile_in.target_salary,
            currency=profile_in.currency
        )
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def get_active_profile(self) -> Optional[CandidateProfile]:
        """Returns the primary active candidate profile (first profile for V1 personal assistant)."""
        query = (
            select(CandidateProfile)
            .order_by(CandidateProfile.created_at.asc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_profile_by_id(self, candidate_id: uuid.UUID) -> CandidateProfile:
        """Returns a candidate profile by UUID or raises EntityNotFoundException."""
        query = select(CandidateProfile).where(CandidateProfile.id == candidate_id)
        result = await self.db.execute(query)
        profile = result.scalar_one_or_none()
        if not profile:
            raise EntityNotFoundException(f"Candidate profile with ID {candidate_id} not found")
        return profile

    async def update_profile(
        self, candidate_id: uuid.UUID, update_in: CandidateProfileUpdate
    ) -> CandidateProfile:
        """Updates candidate profile details."""
        profile = await self.get_profile_by_id(candidate_id)
        update_data = update_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(profile, field, value)

        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    # ==========================================
    # Skills Management & State Machine
    # ==========================================

    async def get_or_create_skill(self, name: str, category: Optional[str] = None) -> Skill:
        """Finds or creates a master skill record."""
        canonical = name.strip().lower()
        query = select(Skill).where(Skill.canonical_name == canonical)
        result = await self.db.execute(query)
        skill = result.scalar_one_or_none()

        if not skill:
            skill = Skill(
                name=name.strip(),
                canonical_name=canonical,
                category=category
            )
            self.db.add(skill)
            await self.db.flush()

        return skill

    async def add_or_update_candidate_skill(
        self, candidate_id: uuid.UUID, skill_in: CandidateSkillCreate
    ) -> CandidateSkill:
        """Adds a skill to candidate with state classification, or updates existing state."""
        profile = await self.get_profile_by_id(candidate_id)
        skill = await self.get_or_create_skill(skill_in.skill_name, skill_in.category)

        query = select(CandidateSkill).where(
            CandidateSkill.candidate_id == candidate_id,
            CandidateSkill.skill_id == skill.id
        )
        result = await self.db.execute(query)
        cand_skill = result.scalar_one_or_none()

        verified_at = utc_now() if skill_in.state == SkillState.VERIFIED else None

        if cand_skill:
            cand_skill.state = skill_in.state
            cand_skill.years_experience = skill_in.years_experience
            cand_skill.confidence_level = skill_in.confidence_level
            cand_skill.evidence_notes = skill_in.evidence_notes
            if skill_in.state == SkillState.VERIFIED and not cand_skill.verified_at:
                cand_skill.verified_at = verified_at
        else:
            cand_skill = CandidateSkill(
                candidate_id=candidate_id,
                skill_id=skill.id,
                state=skill_in.state,
                years_experience=skill_in.years_experience,
                confidence_level=skill_in.confidence_level,
                evidence_notes=skill_in.evidence_notes,
                verified_at=verified_at
            )
            self.db.add(cand_skill)

        await self.db.commit()
        await self.db.refresh(cand_skill)
        return cand_skill

    async def list_candidate_skills(
        self, candidate_id: uuid.UUID, state: Optional[SkillState] = None
    ) -> Sequence[CandidateSkill]:
        """Lists skills for candidate, optionally filtered by state (e.g., VERIFIED)."""
        query = (
            select(CandidateSkill)
            .options(joinedload(CandidateSkill.skill))
            .where(CandidateSkill.candidate_id == candidate_id)
        )
        if state:
            query = query.where(CandidateSkill.state == state)

        result = await self.db.execute(query)
        return result.scalars().all()

    # ==========================================
    # Resume Fact Bank Management
    # ==========================================

    async def add_resume_fact(
        self, candidate_id: uuid.UUID, fact_in: ResumeFactCreate
    ) -> ResumeFact:
        """Adds a structured verifiable fact to the candidate fact bank."""
        await self.get_profile_by_id(candidate_id)

        fact = ResumeFact(
            candidate_id=candidate_id,
            fact_type=fact_in.fact_type,
            title=fact_in.title,
            description=fact_in.description,
            metrics=fact_in.metrics,
            source_reference=fact_in.source_reference,
            verification_status=fact_in.verification_status,
            tags=fact_in.tags
        )
        self.db.add(fact)
        await self.db.commit()
        await self.db.refresh(fact)
        return fact

    async def list_resume_facts(
        self,
        candidate_id: uuid.UUID,
        fact_type: Optional[FactType] = None,
        verification_status: Optional[FactVerificationStatus] = None
    ) -> Sequence[ResumeFact]:
        """Queries facts from the candidate's Resume Fact Bank."""
        query = select(ResumeFact).where(ResumeFact.candidate_id == candidate_id)
        if fact_type:
            query = query.where(ResumeFact.fact_type == fact_type)
        if verification_status:
            query = query.where(ResumeFact.verification_status == verification_status)

        result = await self.db.execute(query)
        return result.scalars().all()

    # ==========================================
    # Experiences & Projects
    # ==========================================

    async def add_experience(
        self, candidate_id: uuid.UUID, exp_in: ExperienceCreate
    ) -> CandidateExperience:
        """Adds a work experience record."""
        await self.get_profile_by_id(candidate_id)
        exp = CandidateExperience(
            candidate_id=candidate_id,
            company=exp_in.company,
            title=exp_in.title,
            location=exp_in.location,
            start_date=exp_in.start_date,
            end_date=exp_in.end_date,
            is_current=exp_in.is_current,
            description=exp_in.description
        )
        self.db.add(exp)
        await self.db.commit()
        await self.db.refresh(exp)
        return exp

    async def add_project(
        self, candidate_id: uuid.UUID, proj_in: ProjectCreate
    ) -> CandidateProject:
        """Adds a candidate project record."""
        await self.get_profile_by_id(candidate_id)
        proj = CandidateProject(
            candidate_id=candidate_id,
            name=proj_in.name,
            role=proj_in.role,
            description=proj_in.description,
            tech_stack=proj_in.tech_stack,
            url=proj_in.url,
            repo_url=proj_in.repo_url
        )
        self.db.add(proj)
        await self.db.commit()
        await self.db.refresh(proj)
        return proj
