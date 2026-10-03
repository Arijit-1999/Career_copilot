"""Naukri.com job search and extraction adapter.

Selectors and URL patterns are based on Naukri's 2024 DOM structure.
All selectors are isolated in the ``_SELECTORS`` dict so they can be
updated when Naukri changes their front-end without touching business
logic.

CAPTCHA detection:
  Naukri uses Cloudflare bot-checks and occasional image-based CAPTCHAs
  on high-frequency scraping. We detect these by inspecting the page
  title and known challenge URL fragments.

Pagination:
  Naukri search results use page numbers in the URL (``&start=<N>``).
  We iterate until ``max_results`` is reached or no more listings appear.
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urlencode, quote_plus
from datetime import datetime

from app.browser.enums import CaptchaType, PlatformName
from app.browser.adapters.base import BaseJobAdapter
from app.browser.schemas import (
    JobSearchQuery,
    PlatformSearchResult,
    RawJobListing,
    CaptchaChallenge,
)
from app.jobs.enums import JobSourceType

logger = logging.getLogger("adapter.naukri")

# ---------------------------------------------------------------------------
# DOM Selectors (update these when Naukri redesigns their UI)
# ---------------------------------------------------------------------------
_SELECTORS = {
    # Search results page
    "job_cards": "article.jobTuple",
    "job_title": "a.title",
    "company_name": "a.subTitle",
    "location": "li.location span",
    "experience": "li.experience span",
    "salary": "li.salary span",
    "posted_date": "span.jobAge",
    "job_link": "a.title",
    # Detail / JD page
    "jd_title": "h1.jd-header-title",
    "jd_company": "div.jd-header-comp-name a",
    "jd_description": "div.job-desc",
    "jd_skills": "div.key-skill a",
    # Auth detection
    "logout_button": "a#logout",
    "user_avatar": "div.nI-gNb-drawer__header",
    # CAPTCHA signals
    "captcha_frame": "iframe[src*='captcha']",
    "cloudflare_challenge": "div#cf-challenge-running",
}

_NAUKRI_SEARCH_BASE = "https://www.naukri.com/{keyword}-jobs"
_NAUKRI_SEARCH_PARAMS = "?experience={exp}&location={loc}&start={start}"

# Jobs per page on Naukri's search results.
_PAGE_SIZE = 20


class NaukriAdapter(BaseJobAdapter):
    """Adapter for scraping job listings from Naukri.com."""

    def __init__(self, controller: object) -> None:
        super().__init__(controller, PlatformName.NAUKRI)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # BaseJobAdapter implementation
    # ------------------------------------------------------------------

    async def search(self, query: JobSearchQuery) -> PlatformSearchResult:
        """Search Naukri for jobs matching ``query`` and return raw listings."""
        listings: list[RawJobListing] = []
        errors: list[str] = []
        has_more = False

        keyword_slug = "-".join(query.keywords).lower().replace(" ", "-")
        start_index = 0

        try:
            page = await self._ctrl.new_page()

            while len(listings) < query.max_results:
                url = self._build_search_url(
                    keyword_slug=keyword_slug,
                    location=query.location or "",
                    exp=int(query.min_experience_years or 0),
                    start=start_index,
                )
                await self._ctrl.navigate(page, url)

                # Check for CAPTCHA before proceeding.
                challenge = await self.detect_captcha(url)
                if challenge:
                    errors.append(f"CAPTCHA detected on page {start_index // _PAGE_SIZE + 1}: {challenge.captcha_type}")
                    break

                page_listings = await self._extract_search_page(page, url)
                if not page_listings:
                    break  # No more results.

                listings.extend(page_listings)
                start_index += _PAGE_SIZE

                if len(page_listings) < _PAGE_SIZE:
                    break  # Last page.

            has_more = len(listings) >= query.max_results

        except Exception as exc:
            logger.error("Naukri search failed: %s", exc)
            errors.append(str(exc))

        return PlatformSearchResult(
            platform=self.platform,
            query=query,
            listings=listings[: query.max_results],
            total_found=len(listings),
            has_more_pages=has_more,
            errors=errors,
        )

    async def extract_detail(self, listing_url: str) -> Optional[RawJobListing]:
        """Scrape a full JD from a Naukri listing URL."""
        try:
            page = await self._ctrl.new_page()
            await self._ctrl.navigate(page, listing_url)

            title = await self._safe_text(page, _SELECTORS["jd_title"])
            company = await self._safe_text(page, _SELECTORS["jd_company"])
            description = await self._safe_text(page, _SELECTORS["jd_description"])

            # Extract skill tags
            skill_elements = await page.query_selector_all(_SELECTORS["jd_skills"])
            skills: list[str] = []
            for el in skill_elements:
                text = (await el.inner_text()).strip()
                if text:
                    skills.append(text)

            if not title or not company:
                logger.warning("Could not extract title/company from %s", listing_url)
                return None

            # Derive a stable source_job_id from the URL path.
            source_job_id = self._extract_job_id_from_url(listing_url)

            return RawJobListing(
                source=JobSourceType.NAUKRI,
                source_job_id=source_job_id,
                title=title,
                company=company,
                application_url=listing_url,
                description_raw=description,
                required_skills=skills,
            )

        except Exception as exc:
            logger.error("extract_detail(%s) failed: %s", listing_url, exc)
            return None

    async def is_logged_in(self) -> bool:
        """Return True if Naukri shows logged-in UI elements."""
        try:
            page = await self._ctrl.new_page()
            # Navigate to a lightweight profile-check endpoint.
            await self._ctrl.navigate(page, "https://www.naukri.com/mnjuser/homepage", wait_until="domcontentloaded")
            avatar = await page.query_selector(_SELECTORS["user_avatar"])
            return avatar is not None
        except Exception as exc:
            logger.debug("is_logged_in check failed: %s", exc)
            return False

    async def detect_captcha(self, current_url: str) -> Optional[CaptchaChallenge]:
        """Check the current page for Cloudflare or other CAPTCHA challenges."""
        try:
            page = await self._ctrl.new_page()

            # Cloudflare JS challenge
            cf_elem = await page.query_selector(_SELECTORS["cloudflare_challenge"])
            if cf_elem:
                return CaptchaChallenge(
                    platform=self.platform,
                    captcha_type=CaptchaType.UNKNOWN,
                    current_url=current_url,
                    instructions="Cloudflare challenge detected. Please solve manually in the browser.",
                )

            # Embedded CAPTCHA iframe
            captcha_frame = await page.query_selector(_SELECTORS["captcha_frame"])
            if captcha_frame:
                frame_src = await captcha_frame.get_attribute("src") or ""
                captcha_type = self._classify_captcha_from_url(frame_src)
                return CaptchaChallenge(
                    platform=self.platform,
                    captcha_type=captcha_type,
                    current_url=current_url,
                )

            # Title-based detection (Cloudflare "Just a moment…" page)
            title = await page.title()
            if "just a moment" in title.lower() or "checking your browser" in title.lower():
                return CaptchaChallenge(
                    platform=self.platform,
                    captcha_type=CaptchaType.UNKNOWN,
                    current_url=current_url,
                    instructions="Browser verification page detected.",
                )

        except Exception as exc:
            logger.debug("detect_captcha failed: %s", exc)

        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_search_url(
        self, keyword_slug: str, location: str, exp: int, start: int
    ) -> str:
        """Construct a paginated Naukri search URL."""
        base = f"https://www.naukri.com/{quote_plus(keyword_slug)}-jobs"
        params: dict[str, str] = {}
        if location:
            params["location"] = location
        if exp:
            params["experience"] = str(exp)
        if start:
            params["start"] = str(start)
        if params:
            return f"{base}?{urlencode(params)}"
        return base

    async def _extract_search_page(self, page: object, base_url: str) -> list[RawJobListing]:
        """Extract all job listings from the current search results page."""
        listings: list[RawJobListing] = []
        try:
            cards = await page.query_selector_all(_SELECTORS["job_cards"])  # type: ignore[attr-defined]
            for card in cards:
                try:
                    title = (await (await card.query_selector(_SELECTORS["job_title"])).inner_text()).strip()
                    company = (await (await card.query_selector(_SELECTORS["company_name"])).inner_text()).strip()
                    link_el = await card.query_selector(_SELECTORS["job_link"])
                    link = (await link_el.get_attribute("href") or "").strip()
                    salary_raw = await self._safe_text(card, _SELECTORS["salary"])
                    location_raw = await self._safe_text(card, _SELECTORS["location"])
                    posted = await self._safe_text(card, _SELECTORS["posted_date"])

                    if title and company and link:
                        source_job_id = self._extract_job_id_from_url(link)
                        listings.append(
                            RawJobListing(
                                source=JobSourceType.NAUKRI,
                                source_job_id=source_job_id or link,
                                title=title,
                                company=company,
                                location=location_raw or None,
                                application_url=link,
                                salary_raw=salary_raw or None,
                                posted_date_raw=posted or None,
                            )
                        )
                except Exception as exc:
                    logger.debug("Skipping malformed card: %s", exc)
        except Exception as exc:
            logger.warning("_extract_search_page failed: %s", exc)
        return listings

    @staticmethod
    def _extract_job_id_from_url(url: str) -> str:
        """Extract a stable job ID from a Naukri URL.

        Naukri URLs follow the pattern:
          https://www.naukri.com/<slug>-<job-id>?src=...
        We extract the trailing numeric segment from the path.
        """
        match = re.search(r"-(\d{7,})(?:[?#]|$)", url)
        if match:
            return match.group(1)
        # Fallback: use last path segment.
        path = url.split("?")[0].rstrip("/")
        return path.split("/")[-1] or url
