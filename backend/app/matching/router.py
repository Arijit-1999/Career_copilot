"""REST API router for Deterministic & Vector Hybrid Matching Engine."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.matching.enums import MatchStatus
from app.matching.schemas import (
    MatchJobRequest,
    MatchJobResponse,
    BatchMatchRequest,
    BatchMatchResponse,
    JobMatchSummary
)
from app.matching.service import MatchingService


router = APIRouter(tags=["Matching Engine"])


def get_matching_service(db: AsyncSession = Depends(get_db_session)) -> MatchingService:
    return MatchingService(db)


@router.post("/evaluate", response_model=MatchJobResponse, status_code=status.HTTP_200_OK)
async def evaluate_job_match(
    request: MatchJobRequest,
    service: MatchingService = Depends(get_matching_service)
) -> MatchJobResponse:
    """Evaluates multi-stage match between a candidate/profile and a job with explainability breakdown."""
    return await service.evaluate_job(request)


@router.post("/batch", response_model=BatchMatchResponse, status_code=status.HTTP_200_OK)
async def batch_evaluate_matches(
    request: BatchMatchRequest,
    service: MatchingService = Depends(get_matching_service)
) -> BatchMatchResponse:
    """Batch evaluates candidate/search profile against all active jobs and returns ranked matches."""
    return await service.batch_match(request)


@router.get("/top-matches", response_model=List[JobMatchSummary], status_code=status.HTTP_200_OK)
async def get_top_matches(
    candidate_id: Optional[uuid.UUID] = Query(None, description="Optional candidate ID filter"),
    min_score: float = Query(0.0, ge=0.0, le=100.0, description="Minimum overall match score"),
    status: Optional[MatchStatus] = Query(None, description="Filter by match status"),
    only_passed_filters: bool = Query(True, description="Exclude jobs failing hard filters"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: MatchingService = Depends(get_matching_service)
) -> List[JobMatchSummary]:
    """Retrieves pre-calculated ranked job matches for a candidate."""
    return await service.get_top_matches(
        candidate_id=candidate_id,
        min_score=min_score,
        status=status,
        only_passed_filters=only_passed_filters,
        limit=limit,
        offset=offset
    )


@router.get("/jobs/{job_id}", response_model=MatchJobResponse, status_code=status.HTTP_200_OK)
async def evaluate_job_by_id(
    job_id: uuid.UUID,
    candidate_id: Optional[uuid.UUID] = Query(None),
    search_profile_id: Optional[uuid.UUID] = Query(None),
    strict_filters: bool = Query(True),
    service: MatchingService = Depends(get_matching_service)
) -> MatchJobResponse:
    """Directly evaluates and returns the match breakdown for a specific job ID."""
    req = MatchJobRequest(
        job_id=job_id,
        candidate_id=candidate_id,
        search_profile_id=search_profile_id,
        strict_filters=strict_filters
    )
    return await service.evaluate_job(req)
