"""Service layer for job understanding and structured requirement extraction."""

import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import EntityNotFoundException
from app.common.models import utc_now
from app.jobs.models import Job
from app.extraction.tagger import tagger
from app.extraction.schemas import (
    JDAnalysisRequest,
    JDAnalysisResponse,
    JobUnderstandingResult,
    JobExtractAndPersistResponse
)


class ExtractionService:
    """Orchestrates deterministic parsing and requirement persistence."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_custom_jd(self, request: JDAnalysisRequest) -> JDAnalysisResponse:
        """Analyzes an arbitrary JD without requiring database persistence."""
        result = tagger.analyze_jd(
            title=request.title,
            description=request.description,
            company=request.company
        )
        return JDAnalysisResponse(
            title=request.title,
            company=request.company,
            result=result
        )

    async def extract_and_update_job(self, job_id: uuid.UUID) -> JobExtractAndPersistResponse:
        """Extracts requirements for an ingested job and updates its database record."""
        stmt = select(Job).where(Job.id == job_id)
        res = await self.db.execute(stmt)
        job = res.scalar_one_or_none()

        if not job:
            raise EntityNotFoundException(f"Job with id {job_id} not found", details={"job_id": str(job_id)})

        result = tagger.analyze_jd(
            title=job.title,
            description=job.description_raw or job.description_clean,
            company=job.company
        )

        # Merge extracted skills into Job model
        merged_required = set(job.required_skills or []) | set(result.required_skills)
        merged_preferred = set(job.preferred_skills or []) | set(result.preferred_skills)
        merged_tags = set(job.extracted_tags or []) | set(result.extracted_tags)

        job.required_skills = sorted(list(merged_required))
        job.preferred_skills = sorted(list(merged_preferred))
        job.extracted_tags = sorted(list(merged_tags))

        if result.min_experience_years and (not job.min_experience_years or job.min_experience_years == 0.0):
            job.min_experience_years = result.min_experience_years
        if result.max_experience_years and not job.max_experience_years:
            job.max_experience_years = result.max_experience_years

        job.updated_at = utc_now()
        await self.db.commit()
        await self.db.refresh(job)

        return JobExtractAndPersistResponse(
            job_id=job.id,
            result=result,
            updated_at=job.updated_at.isoformat()
        )
