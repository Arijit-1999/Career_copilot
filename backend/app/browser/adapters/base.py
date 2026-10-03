"""Abstract base interface for all job platform adapters.

Every concrete adapter (Naukri, LinkedIn, Indeed, …) must subclass
``BaseJobAdapter`` and implement all abstract methods. This contract
ensures the rest of the system can treat all platforms uniformly.

Adapter responsibilities:
  1. ``search()``        — Navigate the platform and return raw job listings.
  2. ``extract_detail()``— Scrape full job description from a listing URL.
  3. ``is_logged_in()``  — Detect whether the current browser session is
                           authenticated (used by the session manager).
  4. ``detect_captcha()``— Detect and classify CAPTCHA / bot-detection gates.

Adapters receive an injected ``BrowserController`` so they never directly
import or instantiate Playwright. This makes unit testing trivial — pass
an ``AsyncMock`` and assert on the URLs / selectors used.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

from app.browser.enums import CaptchaType, PlatformName
from app.browser.schemas import (
    JobSearchQuery,
    PlatformSearchResult,
    RawJobListing,
    CaptchaChallenge,
)

if TYPE_CHECKING:
    from app.browser.controller import BrowserController

logger = logging.getLogger(__name__)


class BaseJobAdapter(ABC):
    """Contract every job platform adapter must fulfil.

    Parameters
    ----------
    controller:
        A ``BrowserController`` instance (or ``AsyncMock`` in tests).
    platform:
        The ``PlatformName`` enum value that identifies this adapter.
    """

    def __init__(self, controller: "BrowserController", platform: PlatformName) -> None:
        self._ctrl = controller
        self.platform = platform
        self.logger = logging.getLogger(f"adapter.{platform.value}")

    # ------------------------------------------------------------------
    # Abstract interface — all adapters must implement these
    # ------------------------------------------------------------------

    @abstractmethod
    async def search(self, query: JobSearchQuery) -> PlatformSearchResult:
        """Navigate the platform and return a list of raw job listings.

        Implementations must:
          - Handle pagination up to ``query.max_results``.
          - Return partial results on error (populate ``errors`` field).
          - NOT raise on CAPTCHA — instead, return an empty/partial result
            and let the caller handle the ``CaptchaChallenge`` via
            ``detect_captcha()``.
        """
        ...

    @abstractmethod
    async def extract_detail(self, listing_url: str) -> Optional[RawJobListing]:
        """Scrape full job detail from a single listing URL.

        Returns ``None`` if the page is unavailable or blocked.
        """
        ...

    @abstractmethod
    async def is_logged_in(self) -> bool:
        """Check whether the browser currently has a valid authenticated session.

        Should be a lightweight DOM check (look for user avatar, logout
        button, profile menu, etc.) — avoid triggering navigation.
        """
        ...

    @abstractmethod
    async def detect_captcha(self, current_url: str) -> Optional[CaptchaChallenge]:
        """Inspect the current page for CAPTCHA or bot-detection elements.

        Returns a ``CaptchaChallenge`` if a challenge is detected, else ``None``.
        """
        ...

    # ------------------------------------------------------------------
    # Shared helpers available to all subclasses
    # ------------------------------------------------------------------

    async def _safe_text(self, page: object, selector: str, default: str = "") -> str:
        """Extract trimmed inner text from a selector, returning ``default`` on failure."""
        try:
            element = await page.query_selector(selector)  # type: ignore[attr-defined]
            if element:
                text = await element.inner_text()
                return text.strip()
        except Exception as exc:
            self.logger.debug("_safe_text(%s) failed: %s", selector, exc)
        return default

    async def _safe_attr(self, page: object, selector: str, attr: str, default: str = "") -> str:
        """Extract an attribute from a selector, returning ``default`` on failure."""
        try:
            element = await page.query_selector(selector)  # type: ignore[attr-defined]
            if element:
                value = await element.get_attribute(attr)
                return (value or "").strip()
        except Exception as exc:
            self.logger.debug("_safe_attr(%s[%s]) failed: %s", selector, attr, exc)
        return default

    def _classify_captcha_from_url(self, url: str) -> CaptchaType:
        """Heuristically classify CAPTCHA type from URL patterns."""
        url_lower = url.lower()
        if "recaptcha" in url_lower or "google.com/recaptcha" in url_lower:
            return CaptchaType.RECAPTCHA_V2
        if "hcaptcha" in url_lower:
            return CaptchaType.HCAPTCHA
        return CaptchaType.UNKNOWN
