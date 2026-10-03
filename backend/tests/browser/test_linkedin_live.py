"""Live browser integration test for LinkedIn scraper.

Runs a real Playwright Chromium instance against live LinkedIn.
Marked with `@pytest.mark.browser` so it is excluded from default unit test runs
unless explicitly run with `pytest -m browser`.
"""

import pytest

try:
    import playwright
    PLAYWRIGHT_INSTALLED = True
except ImportError:
    PLAYWRIGHT_INSTALLED = False

from app.browser.controller import BrowserController
from app.browser.adapters.linkedin import LinkedInAdapter
from app.browser.enums import PlatformName
from app.browser.schemas import BrowserConfig, JobSearchQuery


@pytest.mark.browser
@pytest.mark.asyncio
async def test_linkedin_live_search_guest_mode():
    """Live smoke test: verify LinkedInAdapter can search public jobs in headless mode."""
    if not PLAYWRIGHT_INSTALLED:
        pytest.skip("Playwright is not installed. Install with 'pip install playwright && playwright install chromium'")

    config = BrowserConfig(
        headless=True,
        slow_mo_ms=500,
        timeout_ms=30_000,
    )

    try:
        async with await BrowserController.launch(config) as ctrl:
            adapter = LinkedInAdapter(ctrl)

            query = JobSearchQuery(
                keywords=["Python"],
                location="India",
                remote_only=True,
                max_results=3,
            )

            result = await adapter.search(query)

            # Assert structural integrity of search result
            assert result.platform == PlatformName.LINKEDIN
            assert isinstance(result.listings, list)
            assert isinstance(result.errors, list)

            # If listings were returned, verify fields on the first item
            if result.listings:
                first = result.listings[0]
                assert first.title
                assert first.company
                assert first.application_url.startswith("http")
                assert first.source_job_id

    except Exception as exc:
        pytest.fail(f"Live LinkedIn browser search raised an unexpected exception: {exc}")
