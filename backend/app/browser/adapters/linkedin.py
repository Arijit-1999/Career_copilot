"""LinkedIn job search and extraction adapter.

Selectors and URL patterns are based on LinkedIn's 2024 job search DOM.
All selectors are isolated in ``_SELECTORS`` for easy maintenance.

Key differences from Naukri:
  - LinkedIn requires login for full JD access; guest mode returns limited data.
  - Pagination uses an ``&start=<offset>`` query param (25 jobs per page).
  - Auth is detected via the persistent top-nav user avatar / profile photo.
  - LinkedIn aggressively bot-detects: we check for the "authwall" redirect
    and the "challenge" interstitial page.

Rate-limiting strategy:
  - Adapts slow_mo from BrowserConfig automatically.
  - Returns partial results (not empty) so the pipeline can still ingest
    whatever was scraped before a block occurred.
"""

from __future__ import annotations

import re
import logging
from typing import Optional
from urllib.parse import urlencode, quote_plus

from app.browser.enums import CaptchaType, PlatformName
from app.browser.adapters.base import BaseJobAdapter
from app.browser.schemas import (
    JobSearchQuery,
    PlatformSearchResult,
    RawJobListing,
    CaptchaChallenge,
)
from app.jobs.enums import JobSourceType

logger = logging.getLogger("adapter.linkedin")

# ---------------------------------------------------------------------------
# DOM Selectors (update these when LinkedIn redesigns their UI)
# ---------------------------------------------------------------------------
_SELECTORS = {
    # Job search results (guest & logged-in)
    "job_cards": "div.base-card, li.jobs-search-results__list-item, div.job-card-container, div.jobs-search-results-list li, ul.jobs-search__results-list > li",
    "job_title": "h3.base-search-card__title, a.job-card-list__title, .job-card-container__link, strong",
    "company_name": "h4.base-search-card__subtitle, .job-card-container__primary-description, span.job-card-container__company-name, .artdeco-entity-lockup__subtitle",
    "location": "span.job-search-card__location, .job-card-container__metadata-item, .artdeco-entity-lockup__caption",
    "posted_date": "time.job-search-card__listdate, time",
    "job_link": "a.base-card__full-link, a.job-card-list__title, a.job-card-container__link",
    # Job detail page
    "jd_title": "h1.top-card-layout__title, h2.t-24, h1.t-24, .job-details-jobs-unified-top-card__job-title",
    "jd_company": "a.topcard__org-name-link, .job-details-jobs-unified-top-card__company-name, .job-details-jobs-unified-top-card__primary-description a",
    "jd_location": "span.topcard__flavor--bullet, .job-details-jobs-unified-top-card__bullet, .job-details-jobs-unified-top-card__primary-description span",
    "jd_description": "div.show-more-less-html__markup, div#job-details, article.jobs-description__container",
    "jd_skills": "span.job-criteria__text, .job-details-preferences-and-skills",
    # Auth detection
    "user_avatar": "img.global-nav__me-photo, button[aria-label*='Me'], nav.global-nav, div.global-nav__me, a.global-nav__primary-link[href*='/in/']",
    "profile_nav": "div.global-nav__me",
    # Challenge / bot-detection signals
    "authwall": "div.authwall-join-form",
    "challenge_form": "form#challenge-form",
    "captcha_img": "img#captcha-internal",
}

_LINKEDIN_SEARCH_BASE = "https://www.linkedin.com/jobs/search/"
_PAGE_SIZE = 25  # LinkedIn returns 25 cards per page


class LinkedInAdapter(BaseJobAdapter):
    """Adapter for scraping job listings from LinkedIn."""

    def __init__(self, controller: object) -> None:
        super().__init__(controller, PlatformName.LINKEDIN)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # BaseJobAdapter implementation
    # ------------------------------------------------------------------

    async def search(self, query: JobSearchQuery) -> PlatformSearchResult:
        """Search LinkedIn jobs and return raw listings."""
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

                # Check for auth-wall or CAPTCHA before scraping.
                challenge = await self.detect_captcha(url)
                if challenge:
                    errors.append(
                        f"Challenge detected at offset {start_offset}: {challenge.captcha_type}"
                    )
                    break

                page_listings = await self._extract_search_page(page)
                if not page_listings:
                    break  # End of results.

                listings.extend(page_listings)
                start_offset += _PAGE_SIZE

                if len(page_listings) < _PAGE_SIZE:
                    break  # Last page.

            has_more = len(listings) >= query.max_results

        except Exception as exc:
            logger.error("LinkedIn search failed: %s", exc)
            errors.append(str(exc))

        return PlatformSearchResult(
            platform=self.platform,
            query=query,
            listings=listings[: query.max_results],
            total_found=len(listings),
            has_more_pages=has_more,
            errors=errors,
        )

    async def extract_detail(self, listing_url: str, page: Optional[object] = None) -> Optional[RawJobListing]:
        """Scrape full JD from a LinkedIn job listing URL."""
        if listing_url.startswith("/"):
            listing_url = f"https://www.linkedin.com{listing_url}"

        target_page = page
        close_after = False
        try:
            if target_page is None:
                target_page = await self._ctrl.new_page()
                close_after = True
                await self._ctrl.navigate(target_page, listing_url)
            else:
                await self._ctrl.navigate(target_page, listing_url)

            title = await self._safe_text(target_page, _SELECTORS["jd_title"])
            company = await self._safe_text(target_page, _SELECTORS["jd_company"])
            location = await self._safe_text(target_page, _SELECTORS["jd_location"])
            description = await self._safe_text(target_page, _SELECTORS["jd_description"])

            # Extract skill/criteria tags
            skill_elements = await target_page.query_selector_all(_SELECTORS["jd_skills"])
            skills: list[str] = []
            for el in skill_elements:
                text = (await el.inner_text()).strip()
                if text:
                    skills.append(text)

            if not title or not company:
                logger.warning("extract_detail: missing title/company at %s", listing_url)
                return None

            source_job_id = self._extract_job_id_from_url(listing_url)

            return RawJobListing(
                source=JobSourceType.LINKEDIN,
                source_job_id=source_job_id,
                title=title,
                company=company,
                location=location or None,
                application_url=listing_url,
                description_raw=description or None,
                required_skills=skills,
            )

        except Exception as exc:
            logger.error("extract_detail(%s) failed: %s", listing_url, exc)
            return None
        finally:
            if close_after and target_page and hasattr(target_page, "close"):
                try:
                    await target_page.close()
                except Exception:
                    pass

    async def is_logged_in(self, page: Optional[object] = None) -> bool:
        """Return True if LinkedIn shows the authenticated top-nav avatar or nav."""
        try:
            target_page = page
            close_after = False
            if target_page is None:
                target_page = await self._ctrl.new_page()
                close_after = True
                await self._ctrl.navigate(
                    target_page,
                    "https://www.linkedin.com/feed/",
                    wait_until="domcontentloaded",
                )
            avatar = await target_page.query_selector(_SELECTORS["user_avatar"])
            if close_after and hasattr(target_page, "close"):
                try:
                    await target_page.close()
                except Exception:
                    pass
            return avatar is not None
        except Exception as exc:
            logger.debug("is_logged_in check failed: %s", exc)
            return False

    async def detect_captcha(self, current_url: str, page: Optional[object] = None) -> Optional[CaptchaChallenge]:
        """Detect LinkedIn authwall, challenge page, or embedded CAPTCHA."""
        try:
            # URL-based check (fast, no DOM check needed)
            if "/checkpoint/" in current_url or "/authwall" in current_url:
                return CaptchaChallenge(
                    platform=self.platform,
                    captcha_type=CaptchaType.UNKNOWN,
                    current_url=current_url,
                    instructions="LinkedIn checkpoint/authwall URL detected.",
                )

            target_page = page
            if target_page is None:
                target_page = await self._ctrl.new_page()

            # Auth-wall redirect (LinkedIn shows this to unauthenticated scrapers)
            authwall = await target_page.query_selector(_SELECTORS["authwall"])
            if authwall:
                return CaptchaChallenge(
                    platform=self.platform,
                    captcha_type=CaptchaType.UNKNOWN,
                    current_url=current_url,
                    instructions="LinkedIn auth-wall detected. Please log in manually.",
                )

            # Challenge / bot-detection interstitial
            challenge_form = await target_page.query_selector(_SELECTORS["challenge_form"])
            if challenge_form:
                return CaptchaChallenge(
                    platform=self.platform,
                    captcha_type=CaptchaType.IMAGE_CHALLENGE,
                    current_url=current_url,
                    instructions="LinkedIn bot-detection challenge. Solve and resume.",
                )

            # Embedded CAPTCHA image
            captcha_img = await target_page.query_selector(_SELECTORS["captcha_img"])
            if captcha_img:
                return CaptchaChallenge(
                    platform=self.platform,
                    captcha_type=CaptchaType.IMAGE_CHALLENGE,
                    current_url=current_url,
                )

        except Exception as exc:
            logger.debug("detect_captcha failed: %s", exc)

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
        """Construct a paginated LinkedIn job search URL."""
        params: dict[str, str] = {
            "keywords": " ".join(keywords),
            "trk": "public_jobs_jobs-search-bar_search-submit",
        }
        if location:
            params["location"] = location
        if remote_only:
            params["f_WT"] = "2"  # LinkedIn's remote filter code
        if start:
            params["start"] = str(start)
        return f"{_LINKEDIN_SEARCH_BASE}?{urlencode(params)}"

    async def _extract_search_page(self, page: object) -> list[RawJobListing]:
        """Extract all job listings from the current LinkedIn search results page."""
        listings: list[RawJobListing] = []
        try:
            cards = await page.query_selector_all(_SELECTORS["job_cards"])  # type: ignore[attr-defined]
            for card in cards:
                try:
                    title = await self._safe_text(card, _SELECTORS["job_title"])
                    company = await self._safe_text(card, _SELECTORS["company_name"])
                    location = await self._safe_text(card, _SELECTORS["location"])
                    posted = await self._safe_attr(card, _SELECTORS["posted_date"], "datetime")
                    link = await self._safe_attr(card, _SELECTORS["job_link"], "href")

                    if title and company and link:
                        if link.startswith("/"):
                            link = f"https://www.linkedin.com{link}"
                        source_job_id = self._extract_job_id_from_url(link)
                        listings.append(
                            RawJobListing(
                                source=JobSourceType.LINKEDIN,
                                source_job_id=source_job_id or link,
                                title=title,
                                company=company,
                                location=location or None,
                                application_url=link,
                                posted_date_raw=posted or None,
                            )
                        )
                except Exception as exc:
                    logger.debug("Skipping malformed LinkedIn card: %s", exc)
        except Exception as exc:
            logger.warning("_extract_search_page (LinkedIn) failed: %s", exc)
        return listings

    @staticmethod
    def _extract_job_id_from_url(url: str) -> str:
        """Extract the LinkedIn numeric job ID from a job posting URL.

        LinkedIn URLs follow:
          https://www.linkedin.com/jobs/view/<job-id>/
        or search result card links may contain ``currentJobId=<id>``.
        """
        # Primary pattern: /jobs/view/<numeric_id>/
        match = re.search(r"/jobs/view/(\d+)", url)
        if match:
            return match.group(1)
        # Fallback: currentJobId query param
        match = re.search(r"currentJobId=(\d+)", url)
        if match:
            return match.group(1)
        # Last resort: last path segment
        path = url.split("?")[0].rstrip("/")
        return path.split("/")[-1] or url
