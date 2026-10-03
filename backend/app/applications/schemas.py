"""Pydantic v2 schemas (DTOs) for the Application Assistance domain."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.applications.enums import ApplicationStatus, ApplicationAction, AutomationLevel


# ---------------------------------------------------------------------------
# Form Field Mapper Schemas  (APP-001)
# ---------------------------------------------------------------------------

class DetectedFormField(BaseModel):
    """Represents a single form field detected on a job application page."""

    field_name: str = Field(..., description="Raw HTML name/id of the field")
    label: str = Field(..., description="Human-readable label text")
    field_type: str = Field(..., description="HTML input type: text, select, textarea, file, …")
    required: bool = Field(False, description="Whether the field is mandatory")
    options: List[str] = Field(default_factory=list, description="Choices for select/radio fields")
    placeholder: Optional[str] = Field(None, description="Placeholder text if present")


class FormMappingRequest(BaseModel):
    """Request body for the form-field mapper."""

    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    resume_id: Optional[uuid.UUID] = None
    detected_fields: List[DetectedFormField] = Field(
        ..., min_length=1, description="Fields detected on the application page"
    )
    # Raw page context (job title, company) to improve mapping quality
    page_context: Dict[str, Any] = Field(default_factory=dict)


class MappedFormField(BaseModel):
    """A detected field paired with the best candidate value for it."""

    field_name: str
    label: str
    field_type: str
    required: bool
    mapped_value: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Mapping confidence 0-1")
    needs_human_review: bool = Field(
        False, description="True if confidence is too low or value is sensitive"
    )


class FormMappingResult(BaseModel):
    """Full form-mapping result returned by the mapper."""

    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    mapped_fields: List[MappedFormField]
    unmapped_required_fields: List[str] = Field(
        default_factory=list,
        description="Required fields that could not be mapped — must be filled by human"
    )
    overall_confidence: float = Field(0.0, ge=0.0, le=1.0)
    automation_recommendation: AutomationLevel


# ---------------------------------------------------------------------------
# Automation Router Schemas  (APP-002)
# ---------------------------------------------------------------------------

class AutomationDecision(BaseModel):
    """Result of the automation-vs-handoff router for a given application step."""

    application_id: uuid.UUID
    automation_level: AutomationLevel
    reason: str = Field(..., description="Human-readable explanation for the decision")
    blocking_signals: List[str] = Field(
        default_factory=list,
        description="Issues that prevent full automation (CAPTCHA, SSO, unmapped fields, etc.)"
    )
    safe_to_proceed: bool = Field(
        ..., description="True only when level is FULL_AUTO with no blocking signals"
    )


# ---------------------------------------------------------------------------
# Application Lifecycle Schemas  (APP-003 / APP-004)
# ---------------------------------------------------------------------------

class CreateApplicationRequest(BaseModel):
    """Request to start tracking a new job application."""

    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    platform: Optional[str] = Field(None, max_length=50)
    external_job_url: Optional[str] = Field(None, max_length=2048)
    notes: Optional[str] = None


class TransitionApplicationRequest(BaseModel):
    """Request to fire a lifecycle transition on an existing application."""

    action: ApplicationAction
    notes: Optional[str] = None
    # Metadata attached to the transition event
    actor: str = Field("user", description="Who triggered this transition: user | system")


class ApplicationTransitionEvent(BaseModel):
    """A single entry in the transition history audit log."""

    action: ApplicationAction
    from_status: ApplicationStatus
    to_status: ApplicationStatus
    actor: str
    timestamp: datetime
    notes: Optional[str] = None


class AttachResumeRequest(BaseModel):
    """Attach (or replace) the tailored resume for an application."""

    resume_id: uuid.UUID


class ApplicationResponse(BaseModel):
    """Full application detail returned by the API."""

    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID]
    resume_id: Optional[uuid.UUID]
    status: ApplicationStatus
    platform: Optional[str]
    external_job_url: Optional[str]
    external_application_id: Optional[str]
    cover_letter: Optional[str]
    detected_form_fields: Dict[str, Any]
    mapped_field_values: Dict[str, Any]
    automation_level: Optional[str]
    handoff_count: int
    notes: Optional[str]
    transition_history: List[ApplicationTransitionEvent]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _coerce_transition_history(cls, values: Any) -> Any:
        """Ensure transition_history is a list even when loaded from raw JSON."""
        if isinstance(values, dict):
            th = values.get("transition_history")
            if not isinstance(th, list):
                values["transition_history"] = []
        return values


class ApplicationSummary(BaseModel):
    """Compact listing row for the applications list endpoint."""

    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID]
    status: ApplicationStatus
    platform: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpdateApplicationRequest(BaseModel):
    """Partial-update payload (cover letter, notes, external IDs)."""

    cover_letter: Optional[str] = None
    notes: Optional[str] = None
    external_application_id: Optional[str] = Field(None, max_length=255)
