"""REST API router for Resume Intelligence, Tailoring Engine, and Truth Verification."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.resumes.schemas import (
    GenerateTailoredResumeRequest,
    GenerateMasterResumeRequest,
    TailoredResumeResponse,
    TailoredResumeSummary,
    ResumeUpdateRequest
)
from app.resumes.service import ResumeService


router = APIRouter(tags=["Resume Tailoring & Intelligence"])


def get_resume_service(db: AsyncSession = Depends(get_db_session)) -> ResumeService:
    return ResumeService(db)


@router.post("/tailor", response_model=TailoredResumeResponse, status_code=status.HTTP_201_CREATED)
async def generate_tailored_resume(
    request: GenerateTailoredResumeRequest,
    service: ResumeService = Depends(get_resume_service)
) -> TailoredResumeResponse:
    """Generates a zero-hallucination, ATS Markdown resume tailored to a target job."""
    return await service.generate_tailored_resume(request)


@router.post("/master", response_model=TailoredResumeResponse, status_code=status.HTTP_201_CREATED)
async def generate_master_resume(
    request: GenerateMasterResumeRequest,
    service: ResumeService = Depends(get_resume_service)
) -> TailoredResumeResponse:
    """Generates or refreshes the candidate's master technical resume."""
    return await service.generate_master_resume(request)


@router.get("/{resume_id}", response_model=TailoredResumeResponse, status_code=status.HTTP_200_OK)
async def get_resume_by_id(
    resume_id: uuid.UUID,
    service: ResumeService = Depends(get_resume_service)
) -> TailoredResumeResponse:
    """Retrieves full details and rendered markdown of a specific resume."""
    return await service.get_resume(resume_id)


@router.put("/{resume_id}", response_model=TailoredResumeResponse, status_code=status.HTTP_200_OK)
async def update_resume(
    resume_id: uuid.UUID,
    request: ResumeUpdateRequest,
    service: ResumeService = Depends(get_resume_service)
) -> TailoredResumeResponse:
    """Updates markdown content, approval status, or user notes for a resume."""
    return await service.update_resume(resume_id, request)


@router.get("", response_model=List[TailoredResumeSummary], status_code=status.HTTP_200_OK)
async def list_resumes(
    candidate_id: Optional[uuid.UUID] = Query(None, description="Filter by candidate ID"),
    service: ResumeService = Depends(get_resume_service)
) -> List[TailoredResumeSummary]:
    """Lists all master and tailored resumes."""
    return await service.list_resumes(candidate_id)
