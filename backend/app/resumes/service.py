"""Service layer for Master Resume management, JD-Targeted Tailoring, and Truth Validation."""

import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.core.exceptions import EntityNotFoundException
from app.common.models import utc_now
from app.candidate.models import CandidateProfile, CandidateSkill, ResumeFact, CandidateExperience, CandidateProject
from app.jobs.models import Job
from app.resumes.models import TailoredResume
from app.resumes.enums import ResumeStatus
from app.resumes.fact_selector import fact_selector
from app.resumes.validator import truth_validator
from app.resumes.generator import resume_generator
from app.resumes.schemas import (
    GenerateTailoredResumeRequest,
    GenerateMasterResumeRequest,
    TailoredResumeResponse,
    TailoredResumeSummary,
    ResumeUpdateRequest,
    TruthValidationResult
)


class ResumeService:
    """Orchestrates truth-validated resume assembly, tailoring, and storage."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_candidate_with_relations(self, candidate_id: Optional[uuid.UUID] = None) -> CandidateProfile:
        """Retrieves candidate with all skills, facts, experiences, and projects eager-loaded."""
        stmt = (
            select(CandidateProfile)
            .options(
                selectinload(CandidateProfile.skills).selectinload(CandidateSkill.skill),
                selectinload(CandidateProfile.facts),
                selectinload(CandidateProfile.experiences),
                selectinload(CandidateProfile.projects)
            )
        )
        if candidate_id:
            stmt = stmt.where(CandidateProfile.id == candidate_id)

        res = await self.db.execute(stmt)
        candidate = res.scalars().first()

        if not candidate:
            if candidate_id:
                raise EntityNotFoundException(f"Candidate with id {candidate_id} not found")
            # Create default placeholder
            candidate = CandidateProfile(
                full_name="Default Candidate",
                email="candidate@example.com",
                target_roles=["Backend Engineer"],
                location="Remote"
            )
            self.db.add(candidate)
            await self.db.commit()
            await self.db.refresh(candidate)
            return await self.get_candidate_with_relations(candidate.id)

        return candidate

    async def generate_tailored_resume(self, request: GenerateTailoredResumeRequest) -> TailoredResumeResponse:
        """Generates a job-tailored, zero-hallucination ATS Markdown resume."""
        candidate = await self.get_candidate_with_relations(request.candidate_id)

        # Fetch Target Job
        job_res = await self.db.execute(select(Job).where(Job.id == request.job_id))
        job = job_res.scalar_one_or_none()
        if not job:
            raise EntityNotFoundException(f"Job with id {request.job_id} not found")

        # 1. Fact Selection
        content, targeted_skills = fact_selector.select_structured_content(
            candidate=candidate,
            job=job,
            include_claimed=request.include_claimed_skills,
            max_bullets=request.max_bullets_per_experience
        )

        # 2. Truth Validation
        validation_result = truth_validator.validate_content(candidate, content)

        # 3. Render Markdown
        raw_markdown = resume_generator.render_markdown(content)

        # 4. Persist
        resume_title = f"{job.title} — {job.company}"
        tailored_resume = TailoredResume(
            candidate_id=candidate.id,
            job_id=job.id,
            title=resume_title,
            target_role=request.target_role or job.normalized_title,
            raw_markdown=raw_markdown,
            structured_content=content.model_dump(),
            targeted_skills=targeted_skills,
            is_master=False,
            status=ResumeStatus.VERIFIED_TAILORED if validation_result.is_valid else ResumeStatus.DRAFT,
            truth_score=validation_result.truth_score,
            validation_report=validation_result.model_dump()
        )
        self.db.add(tailored_resume)
        await self.db.commit()
        await self.db.refresh(tailored_resume)

        return TailoredResumeResponse(
            id=tailored_resume.id,
            candidate_id=candidate.id,
            job_id=job.id,
            title=tailored_resume.title,
            target_role=tailored_resume.target_role,
            is_master=tailored_resume.is_master,
            status=tailored_resume.status,
            raw_markdown=tailored_resume.raw_markdown,
            structured_content=tailored_resume.structured_content,
            targeted_skills=tailored_resume.targeted_skills,
            truth_score=tailored_resume.truth_score,
            validation_report=tailored_resume.validation_report,
            user_notes=tailored_resume.user_notes,
            created_at=tailored_resume.created_at.isoformat(),
            updated_at=tailored_resume.updated_at.isoformat()
        )

    async def generate_master_resume(self, request: GenerateMasterResumeRequest) -> TailoredResumeResponse:
        """Generates or updates the master technical resume containing all verified facts."""
        candidate = await self.get_candidate_with_relations(request.candidate_id)

        content, targeted_skills = fact_selector.select_structured_content(
            candidate=candidate,
            job=None,
            include_claimed=True,
            max_bullets=6
        )

        validation_result = truth_validator.validate_content(candidate, content)
        raw_markdown = resume_generator.render_markdown(content)

        master_resume = TailoredResume(
            candidate_id=candidate.id,
            job_id=None,
            title=request.title or "Master Technical Resume",
            target_role=candidate.current_title,
            raw_markdown=raw_markdown,
            structured_content=content.model_dump(),
            targeted_skills=targeted_skills,
            is_master=True,
            status=ResumeStatus.APPROVED,
            truth_score=validation_result.truth_score,
            validation_report=validation_result.model_dump()
        )
        self.db.add(master_resume)
        await self.db.commit()
        await self.db.refresh(master_resume)

        return TailoredResumeResponse(
            id=master_resume.id,
            candidate_id=candidate.id,
            job_id=None,
            title=master_resume.title,
            target_role=master_resume.target_role,
            is_master=True,
            status=master_resume.status,
            raw_markdown=master_resume.raw_markdown,
            structured_content=master_resume.structured_content,
            targeted_skills=master_resume.targeted_skills,
            truth_score=master_resume.truth_score,
            validation_report=master_resume.validation_report,
            user_notes=master_resume.user_notes,
            created_at=master_resume.created_at.isoformat(),
            updated_at=master_resume.updated_at.isoformat()
        )

    async def get_resume(self, resume_id: uuid.UUID) -> TailoredResumeResponse:
        """Retrieves a specific resume by ID."""
        stmt = select(TailoredResume).where(TailoredResume.id == resume_id)
        res = await self.db.execute(stmt)
        resume = res.scalar_one_or_none()
        if not resume:
            raise EntityNotFoundException(f"Resume with id {resume_id} not found")

        return TailoredResumeResponse(
            id=resume.id,
            candidate_id=resume.candidate_id,
            job_id=resume.job_id,
            title=resume.title,
            target_role=resume.target_role,
            is_master=resume.is_master,
            status=resume.status,
            raw_markdown=resume.raw_markdown,
            structured_content=resume.structured_content,
            targeted_skills=resume.targeted_skills,
            truth_score=resume.truth_score,
            validation_report=resume.validation_report,
            user_notes=resume.user_notes,
            created_at=resume.created_at.isoformat(),
            updated_at=resume.updated_at.isoformat()
        )

    async def update_resume(self, resume_id: uuid.UUID, request: ResumeUpdateRequest) -> TailoredResumeResponse:
        """Updates markdown content, status, or user notes on an existing resume."""
        stmt = select(TailoredResume).where(TailoredResume.id == resume_id)
        res = await self.db.execute(stmt)
        resume = res.scalar_one_or_none()
        if not resume:
            raise EntityNotFoundException(f"Resume with id {resume_id} not found")

        if request.raw_markdown is not None:
            resume.raw_markdown = request.raw_markdown
        if request.status is not None:
            resume.status = request.status
        if request.user_notes is not None:
            resume.user_notes = request.user_notes

        resume.updated_at = utc_now()
        await self.db.commit()
        await self.db.refresh(resume)

        return TailoredResumeResponse(
            id=resume.id,
            candidate_id=resume.candidate_id,
            job_id=resume.job_id,
            title=resume.title,
            target_role=resume.target_role,
            is_master=resume.is_master,
            status=resume.status,
            raw_markdown=resume.raw_markdown,
            structured_content=resume.structured_content,
            targeted_skills=resume.targeted_skills,
            truth_score=resume.truth_score,
            validation_report=resume.validation_report,
            user_notes=resume.user_notes,
            created_at=resume.created_at.isoformat(),
            updated_at=resume.updated_at.isoformat()
        )

    async def list_resumes(self, candidate_id: Optional[uuid.UUID] = None) -> List[TailoredResumeSummary]:
        """Lists resumes for candidate ordered by latest update."""
        stmt = select(TailoredResume).order_by(desc(TailoredResume.updated_at))
        if candidate_id:
            stmt = stmt.where(TailoredResume.candidate_id == candidate_id)

        res = await self.db.execute(stmt)
        resumes = res.scalars().all()

        return [
            TailoredResumeSummary(
                id=r.id,
                candidate_id=r.candidate_id,
                job_id=r.job_id,
                title=r.title,
                is_master=r.is_master,
                status=r.status,
                truth_score=r.truth_score,
                targeted_skills=r.targeted_skills,
                created_at=r.created_at.isoformat(),
                updated_at=r.updated_at.isoformat()
            )
            for r in resumes
        ]
