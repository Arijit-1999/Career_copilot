"""Enums for candidate domain, skill states, and resume fact bank."""

from enum import Enum


class SkillState(str, Enum):
    """Lifecycle states for candidate skills."""
    VERIFIED = "VERIFIED"          # Proven by resume / candidate evidence (safe for tailored resume)
    CLAIMED = "CLAIMED"            # Claimed by candidate, but lacks verified evidence
    LEARNING = "LEARNING"          # Actively being learned by candidate
    TARGET = "TARGET"              # Required by target roles, planned for future
    NOT_RELEVANT = "NOT_RELEVANT"  # Explicitly rejected or not relevant to career search


class FactType(str, Enum):
    """Categorization for atomic resume facts."""
    EXPERIENCE = "EXPERIENCE"
    PROJECT = "PROJECT"
    ACHIEVEMENT = "ACHIEVEMENT"
    RESPONSIBILITY = "RESPONSIBILITY"
    METRIC = "METRIC"
    CERTIFICATION = "CERTIFICATION"
    EDUCATION = "EDUCATION"


class FactVerificationStatus(str, Enum):
    """Verification status of a candidate fact."""
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    REJECTED = "REJECTED"


class WorkModePreference(str, Enum):
    """Workplace mode preference."""
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ONSITE = "ONSITE"
    FLEXIBLE = "FLEXIBLE"
