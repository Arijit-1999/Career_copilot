"""APP-004: REST API router for Application Assistance domain."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.applications.schemas import (
    ApplicationResponse,
    ApplicationSummary,
    AttachResumeRequest,
    AutomationDecision,
    CreateApplicationRequest,
    FormMappingRequest,
    FormMappingResult,
    TransitionApplicationRequest,
    UpdateApplicationRequest,
)
from app.applications.enums import ApplicationStatus
from app.applications.service import ApplicationService


router = APIRouter(tags=["Application Assistance"])


def get_application_service(db: AsyncSession = Depends(get_db_session)) -> ApplicationService:
    return ApplicationService(db)


# ---------------------------------------------------------------------------
# Application CRUD
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new application tracker",
)
async def create_application(
    request: CreateApplicationRequest,
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Start tracking a new job application in DISCOVERED state."""
    return await service.create_application(request)


@router.get(
    "",
    response_model=List[ApplicationSummary],
    status_code=status.HTTP_200_OK,
    summary="List applications",
)
async def list_applications(
    candidate_id: Optional[uuid.UUID] = Query(None, description="Filter by candidate"),
    status_filter: Optional[ApplicationStatus] = Query(
        None, alias="status", description="Filter by lifecycle status"
    ),
    service: ApplicationService = Depends(get_application_service),
) -> List[ApplicationSummary]:
    """Return a paginated-friendly list of tracked applications."""
    return await service.list_applications(candidate_id=candidate_id, status=status_filter)


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get application detail",
)
async def get_application(
    application_id: uuid.UUID,
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Retrieve full detail for a tracked application, including transition history."""
    return await service.get_application(application_id)


@router.patch(
    "/{application_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update application metadata",
)
async def update_application(
    application_id: uuid.UUID,
    request: UpdateApplicationRequest,
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Partially update cover letter, notes, or external application ID."""
    return await service.update_application(application_id, request)


@router.post(
    "/{application_id}/attach-resume",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Attach a tailored resume to an application",
)
async def attach_resume(
    application_id: uuid.UUID,
    request: AttachResumeRequest,
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Link a TailoredResume to this application record."""
    return await service.attach_resume(application_id, request)


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------

@router.post(
    "/{application_id}/transition",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Fire a lifecycle transition",
)
async def transition_application(
    application_id: uuid.UUID,
    request: TransitionApplicationRequest,
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """
    Advance or revert the application lifecycle state machine.
    Returns a 422 if the action is not valid from the current status.
    """
    return await service.transition(application_id, request)


# ---------------------------------------------------------------------------
# Form mapping  (APP-001)
# ---------------------------------------------------------------------------

@router.post(
    "/{application_id}/map-form",
    response_model=FormMappingResult,
    status_code=status.HTTP_200_OK,
    summary="Map detected form fields to candidate profile",
)
async def map_form_fields(
    application_id: uuid.UUID,
    request: FormMappingRequest,
    service: ApplicationService = Depends(get_application_service),
) -> FormMappingResult:
    """
    Pass the list of detected HTML form fields to the FormFieldMapper.
    Returns a mapping result with confidence scores and automation recommendation.

    Note: This endpoint accepts a flat ``candidate_profile`` via the request body
    for simplicity.  In production the caller should include the profile dict built
    from the CandidateProfile ORM object.
    """
    # Build a minimal candidate_profile dict from request.page_context
    # (the real integration would load the profile from the DB; this keeps
    # the endpoint dependency-light for now)
    candidate_profile: dict = request.page_context.get("candidate_profile", {})
    return await service.map_form_fields(application_id, request, candidate_profile)


# ---------------------------------------------------------------------------
# Automation routing  (APP-002)
# ---------------------------------------------------------------------------

@router.post(
    "/{application_id}/automation-decision",
    response_model=AutomationDecision,
    status_code=status.HTTP_200_OK,
    summary="Get automation routing decision",
)
async def get_automation_decision(
    application_id: uuid.UUID,
    captcha_detected: bool = Query(False, description="Set True if CAPTCHA was detected"),
    sso_detected: bool = Query(False, description="Set True if SSO gate was detected"),
    service: ApplicationService = Depends(get_application_service),
) -> AutomationDecision:
    """
    Evaluate the current application state and return the automation level
    (FULL_AUTO / PARTIAL_AUTO / HUMAN_REQUIRED) for the next submission step.
    """
    return await service.get_automation_decision(
        application_id,
        captcha_detected=captcha_detected,
        sso_detected=sso_detected,
    )
