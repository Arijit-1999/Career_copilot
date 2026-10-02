"""Service layer for job ingestion, normalization, deduplication, and search queries."""

import uuid
from typing import List, Optional, Sequence
from datetime import datetime
from sqlalchemy import select, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.models import Job
from app.jobs.enums import JobSourceType, JobFreshness, JobStatus
from app.candidate.enums import WorkModePreference
from app.jobs.schemas import (
    JobIngestRequest,
    JobResponse,
    JobIngestResult,
    JobBatchIngestRequest,
    JobBatchIngestResponse
)
from app.jobs.normalization import (
    clean_text,
    canonicalize_url,
    normalize_title,
    parse_salary,
    classify_work_mode,
    calculate_freshness
)
from app.jobs.deduplication import DeduplicationEngine, generate_content_hash
from app.core.exceptions import EntityNotFoundException
from app.common.models import utc_now


class JobService:
    """Service managing normalized job ingestion and search queries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_job(self, req: JobIngestRequest) -> JobIngestResult:
        """Normalizes raw job input, runs multi-signal deduplication, and persists."""
        now = utc_now()
        
        # 1. Normalization
        desc_clean = clean_text(req.description)
        norm_title = normalize_title(req.title)
        canon_url = canonicalize_url(req.application_url)
        work_mode = classify_work_mode(
            location=req.location or "Remote",
            title=req.title,
            description=desc_clean,
            explicit_mode=req.work_mode
        )
        
        # Parse salary if not provided numerically
        sal_min, sal_max, currency = req.salary_min, req.salary_max, req.currency or "INR"
        if sal_min is None and sal_max is None and req.salary_raw:
            sal_min, sal_max, currency = parse_salary(req.salary_raw, currency)

        # Generate Content Hash
        content_hash = generate_content_hash(
            company=req.company,
            normalized_title=norm_title,
            description_clean=desc_clean
        )

        # 2. Multi-Signal Deduplication Check
        existing_job = await DeduplicationEngine.find_existing_job(
            db=self.db,
            source=req.source,
            source_job_id=req.source_job_id,
            canonical_url=canon_url,
            content_hash=content_hash,
            company=req.company,
            normalized_title=norm_title,
            location=req.location or "Remote"
        )

        if existing_job:
            # Update last_seen_at timestamp and recalculate freshness
            existing_job.last_seen_at = now
            existing_job.freshness = calculate_freshness(existing_job.posted_at, existing_job.first_seen_at)
            
            # Merge required skills if new ones provided
            if req.required_skills:
                combined_skills = list(set(existing_job.required_skills + req.required_skills))
                existing_job.required_skills = combined_skills

            await self.db.commit()
            await self.db.refresh(existing_job)
            return JobIngestResult(
                job=JobResponse.model_validate(existing_job),
                is_duplicate=True,
                action="seen_again"
            )

        # 3. Create New Normalized Job
        freshness = calculate_freshness(req.posted_at, now)

        job = Job(
            source=req.source,
            source_job_id=req.source_job_id,
            application_url=req.application_url,
            canonical_url=canon_url,
            title=req.title.strip(),
            normalized_title=norm_title,
            company=req.company.strip(),
            location=(req.location or "Remote").strip(),
            work_mode=work_mode,
            employment_type=req.employment_type or "Full-time",
            salary_min=sal_min,
            salary_max=sal_max,
            currency=currency,
            salary_raw=req.salary_raw,
            min_experience_years=req.min_experience_years or 0.0,
            max_experience_years=req.max_experience_years,
            description_raw=req.description,
            description_clean=desc_clean,
            content_hash=content_hash,
            required_skills=req.required_skills,
            preferred_skills=req.preferred_skills,
            extracted_tags=req.required_skills + req.preferred_skills,
            posted_at=req.posted_at,
            first_seen_at=now,
            last_seen_at=now,
            freshness=freshness,
            status=JobStatus.DISCOVERED
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        return JobIngestResult(
            job=JobResponse.model_validate(job),
            is_duplicate=False,
            action="created"
        )

    async def batch_ingest(self, batch_req: JobBatchIngestRequest) -> JobBatchIngestResponse:
        """Batch ingestion processor."""
        results: List[JobIngestResult] = []
        new_count = 0
        dup_count = 0

        for req in batch_req.jobs:
            res = await self.ingest_job(req)
            results.append(res)
            if res.is_duplicate:
                dup_count += 1
            else:
                new_count += 1

        return JobBatchIngestResponse(
            total_received=len(batch_req.jobs),
            new_jobs_added=new_count,
            duplicates_seen=dup_count,
            results=results
        )

    async def list_jobs(
        self,
        keyword: Optional[str] = None,
        company: Optional[str] = None,
        location: Optional[str] = None,
        work_mode: Optional[WorkModePreference] = None,
        freshness: Optional[JobFreshness] = None,
        min_salary: Optional[float] = None,
        source: Optional[JobSourceType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Sequence[Job]:
        """Lists and searches jobs with multi-criteria filtering."""
        query = select(Job).order_by(desc(Job.last_seen_at)).limit(limit).offset(offset)

        if keyword:
            kw = f"%{keyword.strip()}%"
            query = query.where(
                or_(
                    Job.title.ilike(kw),
                    Job.company.ilike(kw),
                    Job.description_clean.ilike(kw)
                )
            )

        if company:
            query = query.where(Job.company.ilike(f"%{company.strip()}%"))

        if location:
            query = query.where(Job.location.ilike(f"%{location.strip()}%"))

        if work_mode:
            query = query.where(Job.work_mode == work_mode)

        if freshness:
            query = query.where(Job.freshness == freshness)

        if min_salary:
            query = query.where(or_(Job.salary_min >= min_salary, Job.salary_max >= min_salary))

        if source:
            query = query.where(Job.source == source)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_job_by_id(self, job_id: uuid.UUID) -> Job:
        """Retrieves a single job by UUID."""
        query = select(Job).where(Job.id == job_id)
        result = await self.db.execute(query)
        job = result.scalar_one_or_none()
        if not job:
            raise EntityNotFoundException(f"Job with ID {job_id} not found")
        return job
