"""REST API router for Job Ingestion, Normalization, Deduplication, and Search."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.jobs.service import JobService
from app.jobs.enums import JobSourceType, JobFreshness
from app.candidate.enums import WorkModePreference
from app.jobs.schemas import (
    JobIngestRequest,
    JobResponse,
    JobIngestResult,
    JobBatchIngestRequest,
    JobBatchIngestResponse
)

router = APIRouter(tags=["Jobs"])


def get_job_service(db: AsyncSession = Depends(get_db_session)) -> JobService:
    return JobService(db)


@router.post("/ingest", response_model=JobIngestResult, status_code=status.HTTP_201_CREATED)
async def ingest_single_job(
    request: JobIngestRequest,
    service: JobService = Depends(get_job_service)
):
    """Ingests a raw job posting, normalizes fields, checks duplicates, and persists."""
    return await service.ingest_job(request)


@router.post("/batch-ingest", response_model=JobBatchIngestResponse, status_code=status.HTTP_201_CREATED)
async def batch_ingest_jobs(
    request: JobBatchIngestRequest,
    service: JobService = Depends(get_job_service)
):
    """Batch ingests multiple job postings from a platform adapter or scraper."""
    return await service.batch_ingest(request)


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    keyword: Optional[str] = Query(None, description="Search across title, company, and description"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    location: Optional[str] = Query(None, description="Filter by location"),
    work_mode: Optional[WorkModePreference] = Query(None, description="Filter by work mode (REMOTE, HYBRID, ONSITE)"),
    freshness: Optional[JobFreshness] = Query(None, description="Filter by freshness level"),
    min_salary: Optional[float] = Query(None, description="Minimum salary threshold"),
    source: Optional[JobSourceType] = Query(None, description="Filter by job source"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: JobService = Depends(get_job_service)
):
    """Searches and filters normalized jobs."""
    jobs = await service.list_jobs(
        keyword=keyword,
        company=company,
        location=location,
        work_mode=work_mode,
        freshness=freshness,
        min_salary=min_salary,
        source=source,
        limit=limit,
        offset=offset
    )
    return [JobResponse.model_validate(j) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_details(
    job_id: uuid.UUID,
    service: JobService = Depends(get_job_service)
):
    """Retrieves full details of a specific job by UUID."""
    job = await service.get_job_by_id(job_id)
    return JobResponse.model_validate(job)
