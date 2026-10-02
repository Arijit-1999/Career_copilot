"""Enums for resume generation, formats, tailoring states, and validation."""

from enum import Enum


class ResumeFormat(str, Enum):
    """Output formats for generated resumes."""
    MARKDOWN = "MARKDOWN"
    JSON_RESUME = "JSON_RESUME"
    PLAIN_TEXT = "PLAIN_TEXT"
    HTML = "HTML"


class ResumeStatus(str, Enum):
    """Lifecycle status of a tailored resume."""
    DRAFT = "DRAFT"
    VERIFIED_TAILORED = "VERIFIED_TAILORED"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


class ValidationSeverity(str, Enum):
    """Severity of a truth validation flag."""
    ERROR = "ERROR"      # Hallucination / unverifiable fact
    WARNING = "WARNING"  # Unverified skill claim
    INFO = "INFO"        # Verified fact
