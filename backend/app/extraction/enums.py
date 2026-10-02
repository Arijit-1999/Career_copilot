"""Enums for job understanding, seniority levels, requirement types, and importance."""

from enum import Enum


class SeniorityLevel(str, Enum):
    """Seniority classification inferred from job title and requirements."""
    INTERN = "INTERN"
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"
    STAFF = "STAFF"
    LEAD = "LEAD"
    PRINCIPAL = "PRINCIPAL"
    DIRECTOR = "DIRECTOR"
    UNSPECIFIED = "UNSPECIFIED"


class RequirementCategory(str, Enum):
    """Domain taxonomy for extracted skills and requirements."""
    LANGUAGE = "LANGUAGE"
    FRAMEWORK = "FRAMEWORK"
    DATABASE = "DATABASE"
    CLOUD_DEVOPS = "CLOUD_DEVOPS"
    AI_ML = "AI_ML"
    VECTOR_SEARCH = "VECTOR_SEARCH"
    TOOL = "TOOL"
    METHODOLOGY = "METHODOLOGY"
    SOFT_SKILL = "SOFT_SKILL"
    DOMAIN = "DOMAIN"


class RequirementImportance(str, Enum):
    """Importance weighting of an extracted JD requirement."""
    MANDATORY = "MANDATORY"
    PREFERRED = "PREFERRED"
    BONUS = "BONUS"
