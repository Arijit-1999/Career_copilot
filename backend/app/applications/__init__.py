"""Public API for the applications domain."""

from app.applications.enums import ApplicationStatus, ApplicationAction, AutomationLevel, VALID_TRANSITIONS
from app.applications.models import JobApplication
from app.applications.schemas import (
    ApplicationResponse,
    ApplicationSummary,
    AttachResumeRequest,
    AutomationDecision,
    CreateApplicationRequest,
    DetectedFormField,
    FormMappingRequest,
    FormMappingResult,
    MappedFormField,
    TransitionApplicationRequest,
    UpdateApplicationRequest,
)
from app.applications.form_mapper import FormFieldMapper
from app.applications.router_logic import ApplicationRouter
from app.applications.service import ApplicationService

__all__ = [
    "ApplicationStatus",
    "ApplicationAction",
    "AutomationLevel",
    "VALID_TRANSITIONS",
    "JobApplication",
    "ApplicationResponse",
    "ApplicationSummary",
    "AttachResumeRequest",
    "AutomationDecision",
    "CreateApplicationRequest",
    "DetectedFormField",
    "FormMappingRequest",
    "FormMappingResult",
    "MappedFormField",
    "TransitionApplicationRequest",
    "UpdateApplicationRequest",
    "FormFieldMapper",
    "ApplicationRouter",
    "ApplicationService",
]
