"""Enums for job pipeline, sources, status, and freshness scoring."""

from enum import Enum


class JobSourceType(str, Enum):
    """Origin source of the job listing."""
    LINKEDIN = "LINKEDIN"
    NAUKRI = "NAUKRI"
    INDEED = "INDEED"
    DIRECT = "DIRECT"
    DIRECT_CAREER_PAGE = "DIRECT_CAREER_PAGE"
    MANUAL = "MANUAL"


class JobFreshness(str, Enum):
    """Categorization of job freshness based on posting/seen age."""
    VERY_FRESH = "VERY_FRESH"    # < 24 hours
    FRESH = "FRESH"              # 1-3 days
    RECENT = "RECENT"            # 4-7 days
    OLDER = "OLDER"              # 8-14 days
    LOW_PRIORITY = "LOW_PRIORITY"# > 14 days


class JobStatus(str, Enum):
    """Lifecycle status of an ingested job."""
    DISCOVERED = "DISCOVERED"
    SHORTLISTED = "SHORTLISTED"
    ARCHIVED = "ARCHIVED"
    EXPIRED = "EXPIRED"
