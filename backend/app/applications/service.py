"""Business-logic service for the Application Assistance domain.

Orchestrates:
- Application creation and lifecycle transitions (APP-003)
- Form field mapping (APP-001)
- Automation routing (APP-002)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.applications.models import JobApplication
from app.applications.enums import (
    ApplicationStatus,
    ApplicationAction,
    AutomationLevel,
    VALID_TRANSITIONS,
)
from app.applications.schemas import (
    ApplicationResponse,
    ApplicationSummary,
    ApplicationTransitionEvent,
    AttachResumeRequest,
    AutomationDecision,
    CreateApplicationRequest,
    FormMappingRequest,
    FormMappingResult,
    TransitionApplicationRequest,
    UpdateApplicationRequest,
)
from app.applications.form_mapper import FormFieldMapper
from app.applications.router_logic import ApplicationRouter
from app.core.exceptions import EntityNotFoundException, ValidationException


class ApplicationService:
    """Service layer for job application lifecycle management."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._router = ApplicationRouter()

    # -----------------------------------------------------------------------
    # CRUD helpers
    # -----------------------------------------------------------------------

    async def _get_or_404(self, application_id: uuid.UUID) -> JobApplication:
        result = await self._db.execute(
            select(JobApplication).where(JobApplication.id == application_id)
        )
        app = result.scalar_one_or_none()
        if app is None:
            raise EntityNotFoundException(
                "JobApplication", str(application_id)
            )
        return app

    # -----------------------------------------------------------------------
    # Creation
    # -----------------------------------------------------------------------

    async def create_application(
        self, request: CreateApplicationRequest
    ) -> ApplicationResponse:
        """Start tracking a new job application in DISCOVERED state."""
        app = JobApplication(
            id=uuid.uuid4(),
            candidate_id=request.candidate_id,
            job_id=request.job_id,
            platform=request.platform,
            external_job_url=str(request.external_job_url) if request.external_job_url else None,
            status=ApplicationStatus.DISCOVERED,
            notes=request.notes,
            detected_form_fields={},
            mapped_field_values={},
            transition_history=[],
            handoff_count=0,
        )
        self._db.add(app)
        await self._db.commit()
        await self._db.refresh(app)
        return self._to_response(app)

    # -----------------------------------------------------------------------
    # Retrieval
    # -----------------------------------------------------------------------

    async def get_application(self, application_id: uuid.UUID) -> ApplicationResponse:
        app = await self._get_or_404(application_id)
        return self._to_response(app)

    async def list_applications(
        self,
        candidate_id: Optional[uuid.UUID] = None,
        status: Optional[ApplicationStatus] = None,
    ) -> List[ApplicationSummary]:
        q = select(JobApplication).order_by(JobApplication.created_at.desc())
        if candidate_id is not None:
            q = q.where(JobApplication.candidate_id == candidate_id)
        if status is not None:
            q = q.where(JobApplication.status == status)
        result = await self._db.execute(q)
        return [ApplicationSummary.model_validate(a) for a in result.scalars().all()]

    # -----------------------------------------------------------------------
    # Lifecycle transitions (APP-003)
    # -----------------------------------------------------------------------

    async def transition(
        self,
        application_id: uuid.UUID,
        request: TransitionApplicationRequest,
    ) -> ApplicationResponse:
        """Fire a lifecycle action and persist the new status."""
        app = await self._get_or_404(application_id)
        key = (app.status, request.action)
        new_status = VALID_TRANSITIONS.get(key)
        if new_status is None:
            raise ValidationException(
                "Invalid transition",
                details={
                    "current_status": app.status,
                    "action": request.action,
                    "valid_actions": [
                        a.value for (s, a) in VALID_TRANSITIONS if s == app.status
                    ],
                },
            )

        event = {
            "action": request.action.value,
            "from_status": app.status.value,
            "to_status": new_status.value,
            "actor": request.actor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": request.notes,
        }
        history: list = list(app.transition_history) if app.transition_history else []
        history.append(event)

        app.status = new_status
        app.transition_history = history
        if request.notes:
            app.notes = request.notes

        await self._db.commit()
        await self._db.refresh(app)
        return self._to_response(app)

    # -----------------------------------------------------------------------
    # Partial update
    # -----------------------------------------------------------------------

    async def update_application(
        self,
        application_id: uuid.UUID,
        request: UpdateApplicationRequest,
    ) -> ApplicationResponse:
        app = await self._get_or_404(application_id)
        if request.cover_letter is not None:
            app.cover_letter = request.cover_letter
        if request.notes is not None:
            app.notes = request.notes
        if request.external_application_id is not None:
            app.external_application_id = request.external_application_id
        await self._db.commit()
        await self._db.refresh(app)
        return self._to_response(app)

    async def attach_resume(
        self,
        application_id: uuid.UUID,
        request: AttachResumeRequest,
    ) -> ApplicationResponse:
        app = await self._get_or_404(application_id)
        app.resume_id = request.resume_id
        await self._db.commit()
        await self._db.refresh(app)
        return self._to_response(app)

    # -----------------------------------------------------------------------
    # Form mapping  (APP-001)
    # -----------------------------------------------------------------------

    async def map_form_fields(
        self,
        application_id: uuid.UUID,
        request: FormMappingRequest,
        candidate_profile: Dict[str, Any],
    ) -> FormMappingResult:
        """
        Map detected form fields to candidate profile values and persist the snapshot.
        ``candidate_profile`` is a plain dict built by the caller from
        ``CandidateProfile`` ORM fields.
        """
        app = await self._get_or_404(application_id)

        mapper = FormFieldMapper(candidate_profile)
        result = mapper.map(request)

        # Persist the snapshot
        app.detected_form_fields = {
            f.field_name: f.model_dump() for f in request.detected_fields
        }
        app.mapped_field_values = {
            f.field_name: f.mapped_value
            for f in result.mapped_fields
            if f.mapped_value is not None
        }
        app.automation_level = result.automation_recommendation.value

        await self._db.commit()
        return result

    # -----------------------------------------------------------------------
    # Automation routing  (APP-002)
    # -----------------------------------------------------------------------

    async def get_automation_decision(
        self,
        application_id: uuid.UUID,
        captcha_detected: bool = False,
        sso_detected: bool = False,
    ) -> AutomationDecision:
        """Return an AutomationDecision for the next submission step."""
        app = await self._get_or_404(application_id)

        # Pull unmapped required fields from persisted form data
        unmapped: List[str] = []
        for field_name, field_data in (app.detected_form_fields or {}).items():
            if isinstance(field_data, dict) and field_data.get("required"):
                if not (app.mapped_field_values or {}).get(field_name):
                    unmapped.append(field_name)

        mapper_level = AutomationLevel(app.automation_level) if app.automation_level else AutomationLevel.HUMAN_REQUIRED

        decision = self._router.route(
            application_id=app.id,
            platform=app.platform,
            automation_level_from_mapper=mapper_level,
            unmapped_required_fields=unmapped,
            captcha_detected=captcha_detected,
            sso_detected=sso_detected,
            previous_handoff_count=app.handoff_count,
        )

        # Increment handoff counter if a handoff is needed
        if decision.automation_level == AutomationLevel.HUMAN_REQUIRED:
            app.handoff_count = (app.handoff_count or 0) + 1
            await self._db.commit()

        return decision

    # -----------------------------------------------------------------------
    # Serialisation helper
    # -----------------------------------------------------------------------

    @staticmethod
    def _to_response(app: JobApplication) -> ApplicationResponse:
        history_raw = app.transition_history if isinstance(app.transition_history, list) else []
        history = [
            ApplicationTransitionEvent(
                action=ApplicationAction(e["action"]),
                from_status=ApplicationStatus(e["from_status"]),
                to_status=ApplicationStatus(e["to_status"]),
                actor=e.get("actor", "system"),
                timestamp=datetime.fromisoformat(e["timestamp"]),
                notes=e.get("notes"),
            )
            for e in history_raw
            if isinstance(e, dict)
        ]
        return ApplicationResponse(
            id=app.id,
            candidate_id=app.candidate_id,
            job_id=app.job_id,
            resume_id=app.resume_id,
            status=app.status,
            platform=app.platform,
            external_job_url=app.external_job_url,
            external_application_id=app.external_application_id,
            cover_letter=app.cover_letter,
            detected_form_fields=app.detected_form_fields or {},
            mapped_field_values=app.mapped_field_values or {},
            automation_level=app.automation_level,
            handoff_count=app.handoff_count or 0,
            notes=app.notes,
            transition_history=history,
            created_at=app.created_at,
            updated_at=app.updated_at,
        )
