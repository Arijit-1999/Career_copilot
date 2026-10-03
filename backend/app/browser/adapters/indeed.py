"""Indeed job search and extraction adapter.

Selectors and URL patterns are based on Indeed's 2024 job search DOM.
All selectors are isolated in ``_SELECTORS`` for easy maintenance.

Key differences from LinkedIn/Naukri:
  - Indeed uses a mosaic tile-based result layout; job cards use ``data-jk``
    attributes as stable job IDs.
  - Indeed India (in.indeed.com) and global (indeed.com) share the same DOM
    structure; the base URL is configurable.
  - Detail pages are loaded in an inline panel (SPA) but also accessible
    via direct URL: ``https://in.indeed.com/viewjob?jk=<jk_id>``.
  - Bot detection comes as a "robot check" page with a Cloudflare CAPTCHA.
"""

from __future__ import annotations

import re
import logging
from typing import Optional
from urllib.parse import urlencode

from app.browser.enums import CaptchaType, PlatformName
from app.browser.adapters.base import BaseJobAdapter
from app.browser.schemas import (
    JobSearchQuery,
    PlatformSearchResult,
    RawJobListing,
    CaptchaChallenge,
)
from app.jobs.enums import JobSourceType

logger = logging.getLogger("adapter.indeed")

# ---------------------------------------------------------------------------
# DOM Selectors (update when Indeed redesigns)
# ---------------------------------------------------------------------------
_SELECTORS = {
    # Search results
    "job_cards": "div.job_seen_beacon",
    "job_title": "h2.jobTitle span[title]",
    "company_name": "span.companyName",
    "location": "div.companyLocation",
    "salary": "div.salary-snippet-container",
    "posted_date": "span.date",
    "job_link": "h2.jobTitle a",
    # Detail page (viewjob)
    "jd_title": "h1.jobsearch-JobInfoHeader-title",
    "jd_company": "div.jobsearch-InlineCompanyRating a",
    "jd_location": "div.jobsearch-JobInfoHeader-subtitle div:nth-child(2)",
    "jd_description": "div#jobDescriptionText",
    "jd_skills": "span.skill-tag",
    # Auth (Indeed doesn't require login for basic search)
    "user_menu": "a#logged-in-button",
    # Bot detection
    "robot_check": "div#captcha-box",
    "cloudflare_challenge": "div#cf-challenge-running",
    "robot_title_keyword": "indeed robot",
}

_INDEED_BASE = "https://in.indeed.com"  # India domain; swap to indeed.com for global
_PAGE_SIZE = 15  # Indeed returns ~15 results per page


class IndeedAdapter(BaseJobAdapter):
    """Adapter for scraping job listings from Indeed (India)."""

    def __init__(self, controller: object, base_url: str = _INDEED_BASE) -> None:
        super().__init__(controller, PlatformName.INDEED)  # type: ignore[arg-type]
        self._base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # BaseJobAdapter implementation
    # ------------------------------------------------------------------

    async def search(self, query: JobSearchQuery) -> PlatformSearchResult:
        """Search Indeed for jobs matching ``query`` and return raw listings."""
        listings: list[RawJobListing] = []
        errors: list[str] = []
        has_more = False
        start_offset = 0

        try:
            page = await self._ctrl.new_page()

            while len(listings) < query.max_results:
                url = self._build_search_url(
                    keywords=query.keywords,
                    location=query.location,
                    remote_only=query.remote_only,
                    start=start_offset,
                )
                await self._ctrl.navigate(page, url)

                challenge = await self.detect_captcha(url)
                if challenge:
                    errors.append(
                        f"Bot-check at offset {start_offset}: {challenge.captcha_type}"
                    )
                    break

                page_listings = await self._extract_search_page(page)
                if not page_listings:
                    break  # No more results.

                listings.extend(page_listings)
                start_offset += _PAGE_SIZE

                if len(page_listings) < _PAGE_SIZE:
                    break  # Last page.

            has_more = len(listings) >= query.max_results

        except Exception as exc:
            logger.error("Indeed search failed: %s", exc)
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
        """Scrape full JD from an Indeed viewjob URL."""
        try:
            # Normalise to canonical viewjob URL using jk param.
            jk = self._extract_job_id_from_url(listing_url)
            canonical_url = f"{self._base_url}/viewjob?jk={jk}" if jk else listing_url

            page = await self._ctrl.new_page()
            await self._ctrl.navigate(page, canonical_url)

            title = await self._safe_text(page, _SELECTORS["jd_title"])
            company = await self._safe_text(page, _SELECTORS["jd_company"])
            location = await self._safe_text(page, _SELECTORS["jd_location"])
            description = await self._safe_text(page, _SELECTORS["jd_description"])

            # Extract skill tags if present
            skill_elements = await page.query_selector_all(_SELECTORS["jd_skills"])
            skills: list[str] = []
            for el in skill_elements:
                text = (await el.inner_text()).strip()
                if text:
                    skills.append(text)

            if not title or not company:
                logger.warning("extract_detail: missing title/company at %s", canonical_url)
                return None

            return RawJobListing(
                source=JobSourceType.INDEED,
                source_job_id=jk or canonical_url,
                title=title,
                company=company,
                location=location or None,
                application_url=canonical_url,
                description_raw=description or None,
                required_skills=skills,
            )

        except Exception as exc:
            logger.error("extract_detail(%s) failed: %s", listing_url, exc)
            return None

    async def is_logged_in(self) -> bool:
        """Return True if Indeed shows a logged-in user menu button."""
        try:
            page = await self._ctrl.new_page()
            await self._ctrl.navigate(
                page,
                f"{self._base_url}/",
                wait_until="domcontentloaded",
            )
            menu = await page.query_selector(_SELECTORS["user_menu"])
            return menu is not None
        except Exception as exc:
            logger.debug("is_logged_in check failed: %s", exc)
            return False

    async def detect_captcha(self, current_url: str) -> Optional[CaptchaChallenge]:
        """Detect Indeed robot-check page or Cloudflare challenge."""
        try:
            page = await self._ctrl.new_page()

            # Cloudflare JS challenge element
            cf_elem = await page.query_selector(_SELECTORS["cloudflare_challenge"])
            if cf_elem:
                return CaptchaChallenge(
                    platform=self.platform,
                    captcha_type=CaptchaType.UNKNOWN,
                    current_url=current_url,
                    instructions="Cloudflare challenge on Indeed. Please resolve manually.",
                )

            # Indeed's native robot-check CAPTCHA box
            robot_box = await page.query_selector(_SELECTORS["robot_check"])
            if robot_box:
                return CaptchaChallenge(
                    platform=self.platform,
                    captcha_type=CaptchaType.IMAGE_CHALLENGE,
                    current_url=current_url,
                    instructions="Indeed robot-check CAPTCHA detected. Please solve manually.",
                )

            # Title-based detection
            title = await page.title()
            if _SELECTORS["robot_title_keyword"] in title.lower():
                return CaptchaChallenge(
                    platform=self.platform,
                    captcha_type=CaptchaType.IMAGE_CHALLENGE,
                    current_url=current_url,
                    instructions="Indeed 'robot' page detected via title.",
                )

        except Exception as exc:
            logger.debug("detect_captcha (Indeed) failed: %s", exc)

        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_search_url(
        self,
        keywords: list[str],
        location: Optional[str],
        remote_only: bool,
        start: int,
    ) -> str:
        """Construct a paginated Indeed job search URL."""
        params: dict[str, str] = {"q": " ".join(keywords)}
        if location:
            params["l"] = location
        if remote_only:
            params["remotejob"] = "032b3046-06a3-4876-8dfd-474eb5e7ed11"  # Indeed's remote filter GUID
        if start:
            params["start"] = str(start)
        return f"{self._base_url}/jobs?{urlencode(params)}"

    async def _extract_search_page(self, page: object) -> list[RawJobListing]:
        """Extract all job listings from the current Indeed search results page."""
        listings: list[RawJobListing] = []
        try:
            cards = await page.query_selector_all(_SELECTORS["job_cards"])  # type: ignore[attr-defined]
            for card in cards:
                try:
                    title = await self._safe_text(card, _SELECTORS["job_title"])
                    company = await self._safe_text(card, _SELECTORS["company_name"])
                    location = await self._safe_text(card, _SELECTORS["location"])
                    salary = await self._safe_text(card, _SELECTORS["salary"])
                    posted = await self._safe_text(card, _SELECTORS["posted_date"])

                    # Job link — href is a relative path like /rc/clk?jk=<id>
                    link_el = await card.query_selector(_SELECTORS["job_link"])
                    relative_href = await link_el.get_attribute("href") if link_el else ""
                    link = (
                        f"{self._base_url}{relative_href}"
                        if relative_href and relative_href.startswith("/")
                        else relative_href or ""
                    )

                    # data-jk is the stable job key on Indeed cards
                    jk = await card.get_attribute("data-jk") if hasattr(card, "get_attribute") else ""
                    source_job_id = jk or self._extract_job_id_from_url(link) or link

                    if title and company:
                        listings.append(
                            RawJobListing(
                                source=JobSourceType.INDEED,
                                source_job_id=source_job_id,
                                title=title,
                                company=company,
                                location=location or None,
                                application_url=link or f"{self._base_url}/viewjob?jk={source_job_id}",
                                salary_raw=salary or None,
                                posted_date_raw=posted or None,
                            )
                        )
                except Exception as exc:
                    logger.debug("Skipping malformed Indeed card: %s", exc)
        except Exception as exc:
            logger.warning("_extract_search_page (Indeed) failed: %s", exc)
        return listings

    @staticmethod
    def _extract_job_id_from_url(url: str) -> str:
        """Extract Indeed job key (``jk``) from a URL.

        Indeed job URLs use ``?jk=<alphanum_id>`` or ``/clk?jk=<id>``.
        """
        match = re.search(r"[?&]jk=([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        # Fallback: last path segment
        path = url.split("?")[0].rstrip("/")
        return path.split("/")[-1] or url
