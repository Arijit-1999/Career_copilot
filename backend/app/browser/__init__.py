"""Browser acquisition package for Career Copilot.

Exports the primary public API of the browser domain.
"""

from app.browser.controller import BrowserController
from app.browser.session import SessionManager
from app.browser.handoff import HumanHandoffService
from app.browser.enums import BrowserState, SessionState, CaptchaType, PlatformName
from app.browser.schemas import (
    BrowserConfig,
    JobSearchQuery,
    PlatformSearchResult,
    RawJobListing,
    CaptchaChallenge,
    HumanTakeoverRequest,
    HumanTakeoverResult,
)
from app.browser.adapters import (
    BaseJobAdapter,
    NaukriAdapter,
    LinkedInAdapter,
    IndeedAdapter,
)

__all__ = [
    "BrowserController",
    "SessionManager",
    "HumanHandoffService",
    "BrowserState",
    "SessionState",
    "CaptchaType",
    "PlatformName",
    "BrowserConfig",
    "JobSearchQuery",
    "PlatformSearchResult",
    "RawJobListing",
    "CaptchaChallenge",
    "HumanTakeoverRequest",
    "HumanTakeoverResult",
    "BaseJobAdapter",
    "NaukriAdapter",
    "LinkedInAdapter",
    "IndeedAdapter",
]

