"""Service layer for Candidate-Job Matching and Match persistence."""

import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.core.exceptions import EntityNotFoundException
from app.common.models import utc_now
from app.candidate.models import CandidateProfile, CandidateSkill, CandidateExperience, Skill
from app.career_profiles.models import CareerSearchProfile
from app.jobs.models import Job
from app.matching.models import JobMatch
from app.matching.enums import MatchStatus
from app.matching.engine import matching_engine
from app.matching.schemas import (
    MatchJobRequest,
    MatchJobResponse,
    BatchMatchRequest,
    BatchMatchResponse,
    JobMatchSummary,
    MatchScoreBreakdown
)


class MatchingService:
    """Orchestrates candidate-to-job matching, scoring persistence, and ranking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_default_candidate(self, candidate_id: Optional[uuid.UUID] = None) -> CandidateProfile:
        """Retrieves specified candidate or default active candidate with eager-loaded relations."""
        stmt = (
            select(CandidateProfile)
            .options(
                selectinload(CandidateProfile.skills).selectinload(CandidateSkill.skill),
                selectinload(CandidateProfile.experiences)
            )
        )
        if candidate_id:
            stmt = stmt.where(CandidateProfile.id == candidate_id)

        res = await self.db.execute(stmt)
        candidate = res.scalars().first()

        if not candidate:
            if candidate_id:
                raise EntityNotFoundException(f"Candidate with id {candidate_id} not found")
            # Create a default placeholder profile if none exists
            candidate = CandidateProfile(
                full_name="Default Candidate",
                email="candidate@example.com",
                target_roles=["Backend Engineer", "Python Developer"],
                location="Remote"
            )
            self.db.add(candidate)
            await self.db.commit()
            await self.db.refresh(candidate)
            # Re-fetch with eager loads
            return await self.get_or_default_candidate(candidate.id)

        return candidate

    async def evaluate_job(self, request: MatchJobRequest) -> MatchJobResponse:
        """Evaluates match between candidate and a single job, updating database record."""
        candidate = await self.get_or_default_candidate(request.candidate_id)

        # Fetch Job
        job_res = await self.db.execute(select(Job).where(Job.id == request.job_id))
        job = job_res.scalar_one_or_none()
        if not job:
            raise EntityNotFoundException(f"Job with id {request.job_id} not found")

        # Fetch Search Profile if provided
        search_profile = None
        if request.search_profile_id:
            sp_res = await self.db.execute(
                select(CareerSearchProfile).where(CareerSearchProfile.id == request.search_profile_id)
            )
            search_profile = sp_res.scalar_one_or_none()

        # Run Engine
        breakdown = matching_engine.match(
            candidate=candidate,
            job=job,
            search_profile=search_profile,
            strict_filters=request.strict_filters
        )

        # Determine Status
        if not breakdown.passed_hard_filters:
            match_status = MatchStatus.FILTERED_OUT
        elif breakdown.overall_score >= 80.0:
            match_status = MatchStatus.STRONG_MATCH
        elif breakdown.overall_score >= 60.0:
            match_status = MatchStatus.MODERATE_MATCH
        elif breakdown.overall_score >= 40.0:
            match_status = MatchStatus.WEAK_MATCH
        else:
            match_status = MatchStatus.LOW_MATCH

        # Check existing match record
        match_stmt = select(JobMatch).where(
            JobMatch.candidate_id == candidate.id,
            JobMatch.job_id == job.id
        )
        existing_match = (await self.db.execute(match_stmt)).scalar_one_or_none()

        if existing_match:
            job_match = existing_match
            job_match.search_profile_id = request.search_profile_id
            job_match.overall_score = breakdown.overall_score
            job_match.skill_score = breakdown.skill_score
            job_match.role_score = breakdown.role_score
            job_match.experience_score = breakdown.experience_score
            job_match.location_score = breakdown.location_score
            job_match.status = match_status
            job_match.passed_hard_filters = breakdown.passed_hard_filters
            job_match.filter_rejection_reasons = [r.value for r in breakdown.rejection_reasons]
            job_match.matched_skills = breakdown.matched_skills
            job_match.missing_mandatory_skills = breakdown.missing_mandatory_skills
            job_match.missing_preferred_skills = breakdown.missing_preferred_skills
            job_match.highlights = breakdown.highlights
            job_match.concerns = breakdown.concerns
            job_match.reasoning_summary = breakdown.reasoning_summary
            job_match.updated_at = utc_now()
        else:
            job_match = JobMatch(
                candidate_id=candidate.id,
                job_id=job.id,
                search_profile_id=request.search_profile_id,
                overall_score=breakdown.overall_score,
                skill_score=breakdown.skill_score,
                role_score=breakdown.role_score,
                experience_score=breakdown.experience_score,
                location_score=breakdown.location_score,
                status=match_status,
                passed_hard_filters=breakdown.passed_hard_filters,
                filter_rejection_reasons=[r.value for r in breakdown.rejection_reasons],
                matched_skills=breakdown.matched_skills,
                missing_mandatory_skills=breakdown.missing_mandatory_skills,
                missing_preferred_skills=breakdown.missing_preferred_skills,
                highlights=breakdown.highlights,
                concerns=breakdown.concerns,
                reasoning_summary=breakdown.reasoning_summary
            )
            self.db.add(job_match)

        await self.db.commit()
        await self.db.refresh(job_match)

        return MatchJobResponse(
            id=job_match.id,
            candidate_id=candidate.id,
            job_id=job.id,
            search_profile_id=request.search_profile_id,
            job_title=job.title,
            company=job.company,
            location=job.location,
            work_mode=job.work_mode.value if hasattr(job.work_mode, "value") else str(job.work_mode),
            overall_score=breakdown.overall_score,
            status=match_status,
            breakdown=breakdown
        )

    async def batch_match(self, request: BatchMatchRequest) -> BatchMatchResponse:
        """Evaluates candidate against all active jobs in batch."""
        candidate = await self.get_or_default_candidate(request.candidate_id)

        # Fetch Search Profile if provided
        search_profile = None
        if request.search_profile_id:
            sp_res = await self.db.execute(
                select(CareerSearchProfile).where(CareerSearchProfile.id == request.search_profile_id)
            )
            search_profile = sp_res.scalar_one_or_none()

        # Fetch all active jobs
        jobs_res = await self.db.execute(select(Job))
        jobs = jobs_res.scalars().all()

        evaluated_summaries: List[JobMatchSummary] = []
        for job in jobs:
            breakdown = matching_engine.match(
                candidate=candidate,
                job=job,
                search_profile=search_profile,
                strict_filters=True
            )

            # Determine Status
            if not breakdown.passed_hard_filters:
                match_status = MatchStatus.FILTERED_OUT
            elif breakdown.overall_score >= 80.0:
                match_status = MatchStatus.STRONG_MATCH
            elif breakdown.overall_score >= 60.0:
                match_status = MatchStatus.MODERATE_MATCH
            elif breakdown.overall_score >= 40.0:
                match_status = MatchStatus.WEAK_MATCH
            else:
                match_status = MatchStatus.LOW_MATCH

            # Upsert match
            match_stmt = select(JobMatch).where(
                JobMatch.candidate_id == candidate.id,
                JobMatch.job_id == job.id
            )
            existing_match = (await self.db.execute(match_stmt)).scalar_one_or_none()

            if existing_match:
                job_match = existing_match
                job_match.overall_score = breakdown.overall_score
                job_match.skill_score = breakdown.skill_score
                job_match.role_score = breakdown.role_score
                job_match.experience_score = breakdown.experience_score
                job_match.location_score = breakdown.location_score
                job_match.status = match_status
                job_match.passed_hard_filters = breakdown.passed_hard_filters
                job_match.filter_rejection_reasons = [r.value for r in breakdown.rejection_reasons]
                job_match.matched_skills = breakdown.matched_skills
                job_match.missing_mandatory_skills = breakdown.missing_mandatory_skills
                job_match.missing_preferred_skills = breakdown.missing_preferred_skills
                job_match.highlights = breakdown.highlights
                job_match.concerns = breakdown.concerns
                job_match.reasoning_summary = breakdown.reasoning_summary
                job_match.updated_at = utc_now()
            else:
                job_match = JobMatch(
                    candidate_id=candidate.id,
                    job_id=job.id,
                    search_profile_id=request.search_profile_id,
                    overall_score=breakdown.overall_score,
                    skill_score=breakdown.skill_score,
                    role_score=breakdown.role_score,
                    experience_score=breakdown.experience_score,
                    location_score=breakdown.location_score,
                    status=match_status,
                    passed_hard_filters=breakdown.passed_hard_filters,
                    filter_rejection_reasons=[r.value for r in breakdown.rejection_reasons],
                    matched_skills=breakdown.matched_skills,
                    missing_mandatory_skills=breakdown.missing_mandatory_skills,
                    missing_preferred_skills=breakdown.missing_preferred_skills,
                    highlights=breakdown.highlights,
                    concerns=breakdown.concerns,
                    reasoning_summary=breakdown.reasoning_summary
                )
                self.db.add(job_match)

            await self.db.flush()

            # Filter check for response
            if request.only_passed_filters and not breakdown.passed_hard_filters:
                continue
            if breakdown.overall_score < request.min_score:
                continue

            evaluated_summaries.append(
                JobMatchSummary(
                    match_id=job_match.id,
                    job_id=job.id,
                    job_title=job.title,
                    company=job.company,
                    location=job.location,
                    work_mode=job.work_mode.value if hasattr(job.work_mode, "value") else str(job.work_mode),
                    salary_min=job.salary_min,
                    salary_max=job.salary_max,
                    salary_currency=job.currency,
                    overall_score=breakdown.overall_score,
                    skill_score=breakdown.skill_score,
                    status=match_status,
                    passed_hard_filters=breakdown.passed_hard_filters,
                    matched_skills=breakdown.matched_skills,
                    missing_mandatory_skills=breakdown.missing_mandatory_skills,
                    highlights=breakdown.highlights,
                    is_starred=job_match.is_starred,
                    is_applied=job_match.is_applied,
                    created_at=job_match.created_at.isoformat() if job_match.created_at else utc_now().isoformat()
                )
            )

        await self.db.commit()

        # Sort descending by score
        evaluated_summaries.sort(key=lambda m: m.overall_score, reverse=True)
        paginated_matches = evaluated_summaries[:request.limit]

        return BatchMatchResponse(
            candidate_id=candidate.id,
            total_jobs_evaluated=len(jobs),
            qualified_matches_count=len(evaluated_summaries),
            matches=paginated_matches
        )

    async def get_top_matches(
        self,
        candidate_id: Optional[uuid.UUID] = None,
        min_score: float = 0.0,
        status: Optional[MatchStatus] = None,
        only_passed_filters: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[JobMatchSummary]:
        """Retrieves pre-calculated matches for candidate ordered by score."""
        candidate = await self.get_or_default_candidate(candidate_id)

        stmt = (
            select(JobMatch, Job)
            .join(Job, JobMatch.job_id == Job.id)
            .where(JobMatch.candidate_id == candidate.id)
            .order_by(desc(JobMatch.overall_score))
        )

        if only_passed_filters:
            stmt = stmt.where(JobMatch.passed_hard_filters == True)
        if min_score > 0.0:
            stmt = stmt.where(JobMatch.overall_score >= min_score)
        if status:
            stmt = stmt.where(JobMatch.status == status)

        stmt = stmt.offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        rows = res.all()

        summaries: List[JobMatchSummary] = []
        for match, job in rows:
            summaries.append(
                JobMatchSummary(
                    match_id=match.id,
                    job_id=job.id,
                    job_title=job.title,
                    company=job.company,
                    location=job.location,
                    work_mode=job.work_mode.value if hasattr(job.work_mode, "value") else str(job.work_mode),
                    salary_min=job.salary_min,
                    salary_max=job.salary_max,
                    salary_currency=job.currency,
                    overall_score=match.overall_score,
                    skill_score=match.skill_score,
                    status=match.status,
                    passed_hard_filters=match.passed_hard_filters,
                    matched_skills=match.matched_skills or [],
                    missing_mandatory_skills=match.missing_mandatory_skills or [],
                    highlights=match.highlights or [],
                    is_starred=match.is_starred,
                    is_applied=match.is_applied,
                    created_at=match.created_at.isoformat()
                )
            )

        return summaries
