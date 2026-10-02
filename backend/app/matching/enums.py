"""Enums for candidate-job matching, scoring statuses, and rejection reasons."""

from enum import Enum


class MatchStatus(str, Enum):
    """Categorization of match strength."""
    STRONG_MATCH = "STRONG_MATCH"      # >= 80%
    MODERATE_MATCH = "MODERATE_MATCH"  # 60% - 79%
    WEAK_MATCH = "WEAK_MATCH"          # 40% - 59%
    LOW_MATCH = "LOW_MATCH"            # < 40%
    FILTERED_OUT = "FILTERED_OUT"      # Hard filter violation


class FilterRejectionReason(str, Enum):
    """Deterministic hard filter failure reasons."""
    LOCATION_MISMATCH = "LOCATION_MISMATCH"
    WORK_MODE_MISMATCH = "WORK_MODE_MISMATCH"
    EXPERIENCE_TOO_HIGH = "EXPERIENCE_TOO_HIGH"
    EXPERIENCE_TOO_LOW = "EXPERIENCE_TOO_LOW"
    SALARY_BELOW_MIN = "SALARY_BELOW_MIN"
    EXCLUDED_SKILL_PRESENT = "EXCLUDED_SKILL_PRESENT"
    MISSING_MANDATORY_CORE = "MISSING_MANDATORY_CORE"
    NONE = "NONE"
