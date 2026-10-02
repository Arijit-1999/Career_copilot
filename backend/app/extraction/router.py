"""FastAPI router for job understanding and structured requirement extraction."""

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.extraction.schemas import (
    JDAnalysisRequest,
    JDAnalysisResponse,
    JobExtractAndPersistResponse
)
from app.extraction.service import ExtractionService


router = APIRouter(tags=["Job Understanding & Skill Extraction"])


def get_extraction_service(db: AsyncSession = Depends(get_db_session)) -> ExtractionService:
    return ExtractionService(db)


@router.post("/analyze", response_model=JDAnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_jd(
    request: JDAnalysisRequest,
    service: ExtractionService = Depends(get_extraction_service)
) -> JDAnalysisResponse:
    """Zero-token structured analysis of arbitrary job title and description text."""
    return await service.analyze_custom_jd(request)


@router.post("/jobs/{job_id}/extract", response_model=JobExtractAndPersistResponse, status_code=status.HTTP_200_OK)
async def extract_and_update_job(
    job_id: uuid.UUID,
    service: ExtractionService = Depends(get_extraction_service)
) -> JobExtractAndPersistResponse:
    """Extracts structured requirements and updates an ingested job record."""
    return await service.extract_and_update_job(job_id)
