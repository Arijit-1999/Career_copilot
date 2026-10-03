"""Pydantic v2 schemas for the browser acquisition domain."""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl

from app.browser.enums import BrowserState, SessionState, CaptchaType, PlatformName
from app.jobs.enums import JobSourceType


# ---------------------------------------------------------------------------
# Browser Controller Schemas
# ---------------------------------------------------------------------------

class BrowserConfig(BaseModel):
    """Configuration for launching a managed Playwright browser."""
    headless: bool = True
    slow_mo_ms: int = Field(default=0, ge=0, le=5000, description="Millisecond delay between Playwright actions.")
    viewport_width: int = Field(default=1280, ge=800)
    viewport_height: int = Field(default=900, ge=600)
    timeout_ms: int = Field(default=30_000, ge=5_000, le=120_000)
    locale: str = "en-US"
    timezone_id: str = "Asia/Kolkata"
    extra_http_headers: Dict[str, str] = Field(default_factory=dict)


class BrowserStatus(BaseModel):
    """Snapshot of current browser instance state."""
    state: BrowserState
    current_url: Optional[str] = None
    session_id: Optional[str] = None
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Session Manager Schemas
# ---------------------------------------------------------------------------

class SessionProfile(BaseModel):
    """Represents a stored, reusable authenticated browser session."""
    platform: PlatformName
    username: str
    state: SessionState = SessionState.UNAUTHENTICATED
    cookies: List[Dict[str, Any]] = Field(default_factory=list)
    local_storage: Dict[str, str] = Field(default_factory=dict)
    session_storage: Dict[str, str] = Field(default_factory=dict)
    last_authenticated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    model_config = {"use_enum_values": True}


class SessionSaveRequest(BaseModel):
    """Request to save session cookies + storage state for a platform."""
    platform: PlatformName
    username: str
    cookies: List[Dict[str, Any]]
    local_storage: Dict[str, str] = Field(default_factory=dict)
    session_storage: Dict[str, str] = Field(default_factory=dict)


class SessionLoadResult(BaseModel):
    """Result of attempting to load a saved session."""
    found: bool
    platform: PlatformName
    session_state: SessionState
    username: Optional[str] = None


# ---------------------------------------------------------------------------
# Platform Adapter Schemas
# ---------------------------------------------------------------------------

class JobSearchQuery(BaseModel):
    """Structured job search parameters sent to a platform adapter."""
    keywords: List[str] = Field(min_length=1)
    location: Optional[str] = None
    remote_only: bool = False
    min_experience_years: Optional[float] = None
    max_experience_years: Optional[float] = None
    max_results: int = Field(default=25, ge=1, le=100)


class RawJobListing(BaseModel):
    """Raw data extracted from a single job listing on a platform page."""
    source: JobSourceType
    source_job_id: str
    title: str
    company: str
    location: Optional[str] = None
    application_url: str
    description_raw: Optional[str] = None
    salary_raw: Optional[str] = None
    posted_date_raw: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)


class PlatformSearchResult(BaseModel):
    """Aggregate result from a platform job search operation."""
    platform: PlatformName
    query: JobSearchQuery
    listings: List[RawJobListing]
    total_found: int
    has_more_pages: bool = False
    errors: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# CAPTCHA / Human Takeover Schemas
# ---------------------------------------------------------------------------

class CaptchaChallenge(BaseModel):
    """Describes a CAPTCHA or human-verification challenge requiring handoff."""
    platform: PlatformName
    captcha_type: CaptchaType
    current_url: str
    screenshot_path: Optional[str] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    instructions: str = "Manual resolution required. Solve the challenge in the browser window."


class HumanTakeoverRequest(BaseModel):
    """Signal to pause automation and hand control to a human operator."""
    reason: str
    platform: PlatformName
    current_url: str
    captcha_challenge: Optional[CaptchaChallenge] = None
    timeout_seconds: int = Field(default=300, ge=1, le=3600)


class HumanTakeoverResult(BaseModel):
    """Outcome after the human has resolved the challenge."""
    resolved: bool
    resumed_url: Optional[str] = None
    new_session_state: SessionState = SessionState.AUTHENTICATED
    notes: Optional[str] = None
