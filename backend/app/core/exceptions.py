"""Custom base application exceptions and error handling structures."""

from typing import Any, Dict, Optional


class AppBaseException(Exception):
    """Base exception for Career Copilot."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EntityNotFoundException(AppBaseException):
    """Raised when a requested resource is not found."""
    pass


class ValidationException(AppBaseException):
    """Raised when data validation fails."""
    pass


class LLMServiceException(AppBaseException):
    """Raised when an external LLM request fails."""
    pass


class DuplicateEntityException(AppBaseException):
    """Raised when a duplicate unique entity is detected."""
    pass


class DatabaseConnectionException(AppBaseException):
    """Raised when database connection cannot be established."""
    pass
