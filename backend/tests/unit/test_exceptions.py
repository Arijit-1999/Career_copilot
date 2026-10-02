"""Unit tests for custom exception classes."""

from app.core.exceptions import (
    AppBaseException,
    EntityNotFoundException,
    ValidationException,
    LLMServiceException
)


def test_exception_details():
    """Verify custom exception details handling."""
    exc = EntityNotFoundException("Candidate not found", details={"candidate_id": "123"})
    assert exc.message == "Candidate not found"
    assert exc.details == {"candidate_id": "123"}
    assert isinstance(exc, AppBaseException)


def test_validation_exception():
    """Verify validation exception."""
    exc = ValidationException("Invalid email format")
    assert exc.message == "Invalid email format"
    assert exc.details == {}
