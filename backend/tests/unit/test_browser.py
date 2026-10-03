"""Unit tests for the browser acquisition domain (BRW-001 to BRW-003).

All tests use AsyncMock to simulate Playwright's async API.
No real browser binary is required to run this suite.

Test coverage:
  - BrowserController: stealth headers, state machine, close lifecycle,
    cookie get/set, ImportError on missing playwright
  - SessionManager: save/load/delete/TTL expiry, restore_to_browser,
    capture_from_browser
  - NaukriAdapter: URL builder, job ID extractor, search result parsing,
    CAPTCHA detection, extract_detail, is_logged_in
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.browser.enums import BrowserState, CaptchaType, PlatformName, SessionState
from app.browser.schemas import (
    BrowserConfig,
    JobSearchQuery,
    SessionSaveRequest,
)
from app.browser.controller import BrowserController
from app.browser.session import SessionManager
from app.browser.adapters.naukri import NaukriAdapter


# ===========================================================================
# Fixtures
# ===========================================================================

def _make_mock_browser() -> MagicMock:
    """Return a MagicMock simulating playwright Browser with async context methods."""
    browser = MagicMock()
    # new_context returns an awaitable that yields a mock context
    context = MagicMock()
    context.add_init_script = AsyncMock()
    context.close = AsyncMock()
    context.cookies = AsyncMock(return_value=[{"name": "session", "value": "abc123"}])
    context.add_cookies = AsyncMock()

    # new_page returns a mock page
    page = MagicMock()
    page.set_default_timeout = MagicMock()
    page.goto = AsyncMock()
    page.title = AsyncMock(return_value="Naukri.com - Jobs & Careers")
    page.query_selector = AsyncMock(return_value=None)
    page.query_selector_all = AsyncMock(return_value=[])
    context.new_page = AsyncMock(return_value=page)

    browser.new_context = AsyncMock(return_value=context)
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def mock_browser() -> MagicMock:
    return _make_mock_browser()


@pytest.fixture
def controller(mock_browser: MagicMock) -> BrowserController:
    return BrowserController(browser=mock_browser, config=BrowserConfig())


@pytest.fixture
def session_dir(tmp_path: Path) -> Path:
    return tmp_path / "sessions"


@pytest.fixture
def session_mgr(session_dir: Path) -> SessionManager:
    return SessionManager(sessions_dir=session_dir)


@pytest.fixture
def naukri(controller: BrowserController) -> NaukriAdapter:
    return NaukriAdapter(controller=controller)


# ===========================================================================
# BrowserController Tests
# ===========================================================================

class TestBrowserController:

    def test_initial_state_is_idle(self, controller: BrowserController) -> None:
        status = controller.status()
        assert status.state == BrowserState.IDLE
        assert status.current_url is None

    async def test_new_page_creates_context_and_returns_page(
        self, controller: BrowserController, mock_browser: MagicMock
    ) -> None:
        page = await controller.new_page()
        assert page is not None
        mock_browser.new_context.assert_awaited_once()
        assert controller.status().state == BrowserState.READY

    async def test_navigate_updates_state_and_url(self, controller: BrowserController) -> None:
        page = await controller.new_page()
        url = "https://www.naukri.com"
        await controller.navigate(page, url)
        status = controller.status()
        assert status.state == BrowserState.READY
        assert status.current_url == url

    async def test_second_new_page_reuses_context(
        self, controller: BrowserController, mock_browser: MagicMock
    ) -> None:
        await controller.new_page()
        await controller.new_page()
        # new_context should only be called once
        mock_browser.new_context.assert_awaited_once()

    async def test_close_sets_closed_state(self, controller: BrowserController) -> None:
        await controller.new_page()  # creates context
        await controller.close()
        assert controller.status().state == BrowserState.CLOSED

    async def test_get_cookies_returns_list(self, controller: BrowserController) -> None:
        await controller.new_page()  # ensure context exists
        cookies = await controller.get_cookies()
        assert isinstance(cookies, list)
        assert cookies[0]["name"] == "session"

    async def test_get_cookies_before_context_returns_empty(self, controller: BrowserController) -> None:
        cookies = await controller.get_cookies()
        assert cookies == []

    async def test_set_cookies_calls_add_cookies(
        self, controller: BrowserController, mock_browser: MagicMock
    ) -> None:
        await controller.new_page()
        cookies = [{"name": "auth", "value": "xyz", "domain": ".naukri.com"}]
        await controller.set_cookies(cookies)
        context = mock_browser.new_context.return_value
        context.add_cookies.assert_awaited_once_with(cookies)

    async def test_launch_raises_import_error_without_playwright(self) -> None:
        with patch.dict("sys.modules", {"playwright": None, "playwright.async_api": None}):
            with pytest.raises(ImportError, match="Playwright is not installed"):
                await BrowserController.launch()

    async def test_context_manager_protocol(self, mock_browser: MagicMock) -> None:
        ctrl = BrowserController(browser=mock_browser, config=BrowserConfig())
        async with ctrl as c:
            assert c.status().state == BrowserState.READY
        assert ctrl.status().state == BrowserState.CLOSED

    def test_status_is_pydantic_model(self, controller: BrowserController) -> None:
        from app.browser.schemas import BrowserStatus
        assert isinstance(controller.status(), BrowserStatus)


# ===========================================================================
# SessionManager Tests
# ===========================================================================

class TestSessionManager:

    def _save_req(self, platform: PlatformName = PlatformName.NAUKRI) -> SessionSaveRequest:
        return SessionSaveRequest(
            platform=platform,
            username="test@example.com",
            cookies=[{"name": "session", "value": "abc"}],
            local_storage={"key": "val"},
            session_storage={},
        )

    def test_save_creates_file(self, session_mgr: SessionManager, session_dir: Path) -> None:
        req = self._save_req()
        profile = session_mgr.save_session(req)
        assert profile.state == SessionState.AUTHENTICATED
        # At least one JSON file exists in the sessions dir
        assert len(list(session_dir.glob("*.json"))) == 1

    def test_load_returns_authenticated_for_fresh_session(self, session_mgr: SessionManager) -> None:
        session_mgr.save_session(self._save_req())
        result = session_mgr.load_session(PlatformName.NAUKRI, "test@example.com")
        assert result.found is True
        assert result.session_state == SessionState.AUTHENTICATED

    def test_load_returns_not_found_when_no_session(self, session_mgr: SessionManager) -> None:
        result = session_mgr.load_session(PlatformName.LINKEDIN, "nobody@example.com")
        assert result.found is False
        assert result.session_state == SessionState.UNAUTHENTICATED

    def test_load_returns_expired_for_old_session(
        self, session_mgr: SessionManager, session_dir: Path
    ) -> None:
        req = self._save_req()
        profile = session_mgr.save_session(req)

        # Manually rewrite the file with an old timestamp.
        old_time = datetime.now(tz=timezone.utc) - timedelta(hours=25)
        profile_dict = json.loads(
            (session_dir / list(session_dir.glob("*.json"))[0].name).read_text()
        )
        profile_dict["last_authenticated_at"] = old_time.isoformat()
        list(session_dir.glob("*.json"))[0].write_text(json.dumps(profile_dict))

        result = session_mgr.load_session(PlatformName.NAUKRI, "test@example.com")
        assert result.session_state == SessionState.EXPIRED

    def test_delete_removes_file(self, session_mgr: SessionManager, session_dir: Path) -> None:
        session_mgr.save_session(self._save_req())
        deleted = session_mgr.delete_session(PlatformName.NAUKRI, "test@example.com")
        assert deleted is True
        assert len(list(session_dir.glob("*.json"))) == 0

    def test_delete_nonexistent_returns_false(self, session_mgr: SessionManager) -> None:
        assert session_mgr.delete_session(PlatformName.NAUKRI, "nobody@example.com") is False

    def test_different_platforms_get_different_files(
        self, session_mgr: SessionManager, session_dir: Path
    ) -> None:
        session_mgr.save_session(self._save_req(PlatformName.NAUKRI))
        session_mgr.save_session(self._save_req(PlatformName.LINKEDIN))
        assert len(list(session_dir.glob("*.json"))) == 2

    async def test_restore_to_browser_injects_cookies(
        self, session_mgr: SessionManager, controller: BrowserController, mock_browser: MagicMock
    ) -> None:
        session_mgr.save_session(self._save_req())
        # Create context first
        await controller.new_page()
        restored = await session_mgr.restore_to_browser(controller, PlatformName.NAUKRI, "test@example.com")
        assert restored is True

    async def test_restore_to_browser_returns_false_when_no_session(
        self, session_mgr: SessionManager, controller: BrowserController
    ) -> None:
        result = await session_mgr.restore_to_browser(controller, PlatformName.NAUKRI, "none@example.com")
        assert result is False

    async def test_capture_from_browser_saves_session(
        self, session_mgr: SessionManager, controller: BrowserController, session_dir: Path
    ) -> None:
        await controller.new_page()  # ensure context exists
        profile = await session_mgr.capture_from_browser(
            controller, PlatformName.NAUKRI, "test@example.com"
        )
        assert profile.state == SessionState.AUTHENTICATED
        assert len(profile.cookies) > 0
        assert len(list(session_dir.glob("*.json"))) == 1

    def test_corrupt_session_file_handled_gracefully(
        self, session_mgr: SessionManager, session_dir: Path
    ) -> None:
        # Write invalid JSON
        path = session_dir / "naukri_corrupt.json"
        path.write_text("NOT_VALID_JSON{{{", encoding="utf-8")
        # Manager should not crash
        result = session_mgr.load_session(PlatformName.NAUKRI, "test@example.com")
        assert result.found is False


# ===========================================================================
# NaukriAdapter Tests
# ===========================================================================

class TestNaukriAdapter:

    # --- URL builder ---

    def test_build_search_url_basic(self, naukri: NaukriAdapter) -> None:
        url = naukri._build_search_url("python-developer", location="", exp=0, start=0)
        assert "python-developer" in url
        assert "naukri.com" in url

    def test_build_search_url_with_params(self, naukri: NaukriAdapter) -> None:
        url = naukri._build_search_url("data-scientist", location="Bangalore", exp=3, start=20)
        assert "location=Bangalore" in url
        assert "experience=3" in url
        assert "start=20" in url

    def test_build_search_url_no_extra_params_when_defaults(self, naukri: NaukriAdapter) -> None:
        url = naukri._build_search_url("engineer", location="", exp=0, start=0)
        assert "?" not in url

    # --- Job ID extractor ---

    def test_extract_job_id_from_standard_naukri_url(self, naukri: NaukriAdapter) -> None:
        url = "https://www.naukri.com/job-listings-python-dev-xyz-corp-12345678?src=search"
        job_id = naukri._extract_job_id_from_url(url)
        assert job_id == "12345678"

    def test_extract_job_id_fallback_for_unknown_format(self, naukri: NaukriAdapter) -> None:
        url = "https://www.naukri.com/some-random-path/abc"
        job_id = naukri._extract_job_id_from_url(url)
        assert job_id == "abc"

    # --- CAPTCHA detection ---

    async def test_detect_captcha_returns_none_on_clean_page(
        self, naukri: NaukriAdapter, controller: BrowserController
    ) -> None:
        # Default mock page has no CAPTCHA elements
        result = await naukri.detect_captcha("https://www.naukri.com")
        assert result is None

    async def test_detect_captcha_detects_cloudflare_title(
        self, naukri: NaukriAdapter, controller: BrowserController, mock_browser: MagicMock
    ) -> None:
        # Make page.title return Cloudflare challenge text
        page = mock_browser.new_context.return_value.new_page.return_value
        page.title = AsyncMock(return_value="Just a moment...")
        result = await naukri.detect_captcha("https://www.naukri.com/search")
        assert result is not None
        assert result.platform == PlatformName.NAUKRI

    async def test_detect_captcha_detects_cf_challenge_element(
        self, naukri: NaukriAdapter, controller: BrowserController, mock_browser: MagicMock
    ) -> None:
        page = mock_browser.new_context.return_value.new_page.return_value
        # query_selector returns a truthy element for cf-challenge-running
        cf_elem = MagicMock()
        async def side_effect(selector: str):
            if "cf-challenge-running" in selector:
                return cf_elem
            return None
        page.query_selector = side_effect
        result = await naukri.detect_captcha("https://www.naukri.com")
        assert result is not None
        assert result.captcha_type == CaptchaType.UNKNOWN

    # --- is_logged_in ---

    async def test_is_logged_in_returns_true_when_avatar_found(
        self, naukri: NaukriAdapter, mock_browser: MagicMock
    ) -> None:
        page = mock_browser.new_context.return_value.new_page.return_value
        avatar_elem = MagicMock()
        async def side_effect(selector: str):
            if "nI-gNb-drawer__header" in selector:
                return avatar_elem
            return None
        page.query_selector = side_effect
        result = await naukri.is_logged_in()
        assert result is True

    async def test_is_logged_in_returns_false_when_no_avatar(
        self, naukri: NaukriAdapter
    ) -> None:
        # Default mock returns None for all query_selector calls
        result = await naukri.is_logged_in()
        assert result is False

    # --- search ---

    async def test_search_returns_platform_search_result(self, naukri: NaukriAdapter) -> None:
        query = JobSearchQuery(keywords=["python", "developer"], max_results=5)
        result = await naukri.search(query)
        assert result.platform == PlatformName.NAUKRI
        assert result.query == query
        assert isinstance(result.listings, list)

    async def test_search_returns_empty_listings_on_empty_page(self, naukri: NaukriAdapter) -> None:
        # Default mock returns [] for query_selector_all
        query = JobSearchQuery(keywords=["python"], max_results=10)
        result = await naukri.search(query)
        assert result.listings == []
        assert result.total_found == 0

    async def test_search_respects_max_results(
        self, naukri: NaukriAdapter, mock_browser: MagicMock
    ) -> None:
        # Create 30 fake cards (more than max_results=5)
        page = mock_browser.new_context.return_value.new_page.return_value
        fake_cards = []
        for i in range(30):
            card = MagicMock()
            title_el = MagicMock()
            title_el.inner_text = AsyncMock(return_value=f"Python Developer {i}")
            company_el = MagicMock()
            company_el.inner_text = AsyncMock(return_value=f"Company {i}")
            link_el = MagicMock()
            link_el.get_attribute = AsyncMock(return_value=f"https://www.naukri.com/job-{i}-1234567{i}")
            async def qs(selector: str, _i=i, _title=title_el, _company=company_el, _link=link_el):
                if selector == "a.title":
                    return _link  # used for href
                if selector == "a.subTitle":
                    return _company
                return None
            card.query_selector = qs
            fake_cards.append(card)

        page.query_selector_all = AsyncMock(return_value=fake_cards)
        query = JobSearchQuery(keywords=["python"], max_results=5)
        result = await naukri.search(query)
        # Should be capped at max_results
        assert len(result.listings) <= 5

    # --- extract_detail ---

    async def test_extract_detail_returns_none_on_missing_title(self, naukri: NaukriAdapter) -> None:
        # All selectors return None by default
        result = await naukri.extract_detail("https://www.naukri.com/job-123456789")
        assert result is None

    async def test_extract_detail_returns_listing_when_title_found(
        self, naukri: NaukriAdapter, mock_browser: MagicMock
    ) -> None:
        page = mock_browser.new_context.return_value.new_page.return_value
        title_el = MagicMock()
        title_el.inner_text = AsyncMock(return_value="Senior Python Developer")
        company_el = MagicMock()
        company_el.inner_text = AsyncMock(return_value="Acme Corp")
        desc_el = MagicMock()
        desc_el.inner_text = AsyncMock(return_value="We need a Python expert...")

        async def qs(selector: str):
            if selector == "h1.jd-header-title":
                return title_el
            if selector == "div.jd-header-comp-name a":
                return company_el
            if selector == "div.job-desc":
                return desc_el
            return None

        page.query_selector = qs
        page.query_selector_all = AsyncMock(return_value=[])

        result = await naukri.extract_detail("https://www.naukri.com/job-python-123456789")
        assert result is not None
        assert result.title == "Senior Python Developer"
        assert result.company == "Acme Corp"
        assert result.description_raw == "We need a Python expert..."

    # --- Platform enum ---

    def test_adapter_platform_is_naukri(self, naukri: NaukriAdapter) -> None:
        assert naukri.platform == PlatformName.NAUKRI


# ===========================================================================
# LinkedInAdapter Tests
# ===========================================================================

from app.browser.adapters.linkedin import LinkedInAdapter


@pytest.fixture
def linkedin(controller: BrowserController) -> LinkedInAdapter:
    return LinkedInAdapter(controller=controller)


class TestLinkedInAdapter:

    # --- URL builder ---

    def test_build_search_url_basic(self, linkedin: LinkedInAdapter) -> None:
        url = linkedin._build_search_url(["python", "developer"], location=None, remote_only=False, start=0)
        assert "linkedin.com/jobs/search/" in url
        assert "python+developer" in url or "python%20developer" in url or "python developer" in url.replace("+", " ")

    def test_build_search_url_with_location(self, linkedin: LinkedInAdapter) -> None:
        url = linkedin._build_search_url(["engineer"], location="Bangalore", remote_only=False, start=0)
        assert "Bangalore" in url or "location=Bangalore" in url

    def test_build_search_url_remote_filter(self, linkedin: LinkedInAdapter) -> None:
        url = linkedin._build_search_url(["developer"], location=None, remote_only=True, start=0)
        assert "f_WT=2" in url

    def test_build_search_url_pagination(self, linkedin: LinkedInAdapter) -> None:
        url = linkedin._build_search_url(["qa"], location=None, remote_only=False, start=25)
        assert "start=25" in url

    # --- Job ID extractor ---

    def test_extract_job_id_from_jobs_view_url(self, linkedin: LinkedInAdapter) -> None:
        url = "https://www.linkedin.com/jobs/view/3876543210/?trk=foo"
        assert linkedin._extract_job_id_from_url(url) == "3876543210"

    def test_extract_job_id_from_currentJobId_param(self, linkedin: LinkedInAdapter) -> None:
        url = "https://www.linkedin.com/jobs/search/?currentJobId=9876543210"
        assert linkedin._extract_job_id_from_url(url) == "9876543210"

    def test_extract_job_id_fallback(self, linkedin: LinkedInAdapter) -> None:
        url = "https://www.linkedin.com/jobs/some-random-listing"
        result = linkedin._extract_job_id_from_url(url)
        assert result  # Non-empty fallback

    # --- Platform identity ---

    def test_platform_is_linkedin(self, linkedin: LinkedInAdapter) -> None:
        assert linkedin.platform == PlatformName.LINKEDIN

    # --- detect_captcha ---

    async def test_detect_captcha_returns_none_on_clean_page(self, linkedin: LinkedInAdapter) -> None:
        result = await linkedin.detect_captcha("https://www.linkedin.com/jobs/search/")
        assert result is None

    async def test_detect_captcha_checkpoint_url(self, linkedin: LinkedInAdapter) -> None:
        result = await linkedin.detect_captcha("https://www.linkedin.com/checkpoint/challenge/12345")
        assert result is not None
        assert result.platform == PlatformName.LINKEDIN

    async def test_detect_captcha_authwall_url(self, linkedin: LinkedInAdapter) -> None:
        result = await linkedin.detect_captcha("https://www.linkedin.com/authwall?trk=foo")
        assert result is not None

    async def test_detect_captcha_detects_authwall_element(
        self, linkedin: LinkedInAdapter, mock_browser: MagicMock
    ) -> None:
        page = mock_browser.new_context.return_value.new_page.return_value
        authwall_el = MagicMock()
        async def qs(selector: str):
            if "authwall-join-form" in selector:
                return authwall_el
            return None
        page.query_selector = qs
        result = await linkedin.detect_captcha("https://www.linkedin.com/jobs/")
        assert result is not None
        assert result.captcha_type == CaptchaType.UNKNOWN

    # --- is_logged_in ---

    async def test_is_logged_in_false_by_default(self, linkedin: LinkedInAdapter) -> None:
        result = await linkedin.is_logged_in()
        assert result is False

    async def test_is_logged_in_true_when_avatar_present(
        self, linkedin: LinkedInAdapter, mock_browser: MagicMock
    ) -> None:
        page = mock_browser.new_context.return_value.new_page.return_value
        avatar = MagicMock()
        async def qs(selector: str):
            if "global-nav__me-photo" in selector:
                return avatar
            return None
        page.query_selector = qs
        result = await linkedin.is_logged_in()
        assert result is True

    # --- search ---

    async def test_search_returns_result_schema(self, linkedin: LinkedInAdapter) -> None:
        query = JobSearchQuery(keywords=["python"], max_results=10)
        result = await linkedin.search(query)
        assert result.platform == PlatformName.LINKEDIN
        assert isinstance(result.listings, list)

    async def test_search_empty_on_no_cards(self, linkedin: LinkedInAdapter) -> None:
        query = JobSearchQuery(keywords=["cobol"], max_results=5)
        result = await linkedin.search(query)
        assert result.listings == []

    # --- extract_detail ---

    async def test_extract_detail_returns_none_when_no_title(self, linkedin: LinkedInAdapter) -> None:
        result = await linkedin.extract_detail("https://www.linkedin.com/jobs/view/3876543210/")
        assert result is None

    async def test_extract_detail_returns_listing(
        self, linkedin: LinkedInAdapter, mock_browser: MagicMock
    ) -> None:
        page = mock_browser.new_context.return_value.new_page.return_value
        title_el = MagicMock()
        title_el.inner_text = AsyncMock(return_value="Staff Engineer")
        company_el = MagicMock()
        company_el.inner_text = AsyncMock(return_value="Stripe")

        async def qs(selector: str):
            if "top-card-layout__title" in selector:
                return title_el
            if "topcard__org-name-link" in selector:
                return company_el
            return None

        page.query_selector = qs
        page.query_selector_all = AsyncMock(return_value=[])

        result = await linkedin.extract_detail("https://www.linkedin.com/jobs/view/3876543210/")
        assert result is not None
        assert result.title == "Staff Engineer"
        assert result.company == "Stripe"


# ===========================================================================
# IndeedAdapter Tests
# ===========================================================================

from app.browser.adapters.indeed import IndeedAdapter


@pytest.fixture
def indeed(controller: BrowserController) -> IndeedAdapter:
    return IndeedAdapter(controller=controller)


class TestIndeedAdapter:

    # --- URL builder ---

    def test_build_search_url_basic(self, indeed: IndeedAdapter) -> None:
        url = indeed._build_search_url(["data engineer"], location=None, remote_only=False, start=0)
        assert "indeed.com" in url
        assert "data+engineer" in url or "data%20engineer" in url or "data engineer" in url.replace("+", " ")

    def test_build_search_url_with_location(self, indeed: IndeedAdapter) -> None:
        url = indeed._build_search_url(["analyst"], location="Mumbai", remote_only=False, start=0)
        assert "Mumbai" in url

    def test_build_search_url_remote_filter(self, indeed: IndeedAdapter) -> None:
        url = indeed._build_search_url(["developer"], location=None, remote_only=True, start=0)
        assert "remotejob" in url

    def test_build_search_url_pagination(self, indeed: IndeedAdapter) -> None:
        url = indeed._build_search_url(["qa"], location=None, remote_only=False, start=15)
        assert "start=15" in url

    # --- Job ID extractor ---

    def test_extract_job_id_from_jk_param(self, indeed: IndeedAdapter) -> None:
        url = "https://in.indeed.com/viewjob?jk=abc123def456"
        assert indeed._extract_job_id_from_url(url) == "abc123def456"

    def test_extract_job_id_from_clk_url(self, indeed: IndeedAdapter) -> None:
        url = "https://in.indeed.com/rc/clk?jk=xyz789&fccid=abc"
        assert indeed._extract_job_id_from_url(url) == "xyz789"

    def test_extract_job_id_fallback(self, indeed: IndeedAdapter) -> None:
        url = "https://in.indeed.com/some/path/listing"
        result = indeed._extract_job_id_from_url(url)
        assert result  # Non-empty

    # --- Platform identity ---

    def test_platform_is_indeed(self, indeed: IndeedAdapter) -> None:
        assert indeed.platform == PlatformName.INDEED

    # --- detect_captcha ---

    async def test_detect_captcha_returns_none_on_clean_page(self, indeed: IndeedAdapter) -> None:
        result = await indeed.detect_captcha("https://in.indeed.com/jobs?q=python")
        assert result is None

    async def test_detect_captcha_detects_robot_title(
        self, indeed: IndeedAdapter, mock_browser: MagicMock
    ) -> None:
        page = mock_browser.new_context.return_value.new_page.return_value
        page.title = AsyncMock(return_value="Indeed Robot Check")
        result = await indeed.detect_captcha("https://in.indeed.com/jobs?q=python")
        assert result is not None
        assert result.platform == PlatformName.INDEED

    async def test_detect_captcha_detects_robot_box_element(
        self, indeed: IndeedAdapter, mock_browser: MagicMock
    ) -> None:
        page = mock_browser.new_context.return_value.new_page.return_value
        robot_el = MagicMock()
        async def qs(selector: str):
            if "captcha-box" in selector:
                return robot_el
            return None
        page.query_selector = qs
        result = await indeed.detect_captcha("https://in.indeed.com/")
        assert result is not None
        assert result.captcha_type == CaptchaType.IMAGE_CHALLENGE

    # --- is_logged_in ---

    async def test_is_logged_in_false_by_default(self, indeed: IndeedAdapter) -> None:
        assert await indeed.is_logged_in() is False

    # --- search ---

    async def test_search_returns_result_schema(self, indeed: IndeedAdapter) -> None:
        query = JobSearchQuery(keywords=["backend"], max_results=10)
        result = await indeed.search(query)
        assert result.platform == PlatformName.INDEED
        assert isinstance(result.listings, list)

    async def test_search_empty_on_no_cards(self, indeed: IndeedAdapter) -> None:
        query = JobSearchQuery(keywords=["cobol"], max_results=5)
        result = await indeed.search(query)
        assert result.listings == []

    # --- extract_detail ---

    async def test_extract_detail_returns_none_on_missing_title(self, indeed: IndeedAdapter) -> None:
        result = await indeed.extract_detail("https://in.indeed.com/viewjob?jk=abc123")
        assert result is None

    async def test_extract_detail_returns_listing(
        self, indeed: IndeedAdapter, mock_browser: MagicMock
    ) -> None:
        page = mock_browser.new_context.return_value.new_page.return_value
        title_el = MagicMock()
        title_el.inner_text = AsyncMock(return_value="Data Engineer")
        company_el = MagicMock()
        company_el.inner_text = AsyncMock(return_value="Flipkart")

        async def qs(selector: str):
            if "jobsearch-JobInfoHeader-title" in selector:
                return title_el
            if "jobsearch-InlineCompanyRating" in selector:
                return company_el
            return None

        page.query_selector = qs
        page.query_selector_all = AsyncMock(return_value=[])

        result = await indeed.extract_detail("https://in.indeed.com/viewjob?jk=abc123def456")
        assert result is not None
        assert result.title == "Data Engineer"
        assert result.company == "Flipkart"
        assert result.source_job_id == "abc123def456"

    # --- Custom base URL ---

    def test_custom_base_url(self) -> None:
        mock_ctrl = MagicMock()
        adapter = IndeedAdapter(controller=mock_ctrl, base_url="https://indeed.com")
        assert "indeed.com" in adapter._base_url
        assert "in.indeed.com" not in adapter._base_url


# ===========================================================================
# HumanHandoffService Tests
# ===========================================================================

from app.browser.handoff import HumanHandoffService
from app.browser.schemas import HumanTakeoverRequest


@pytest.fixture
def handoff_service(controller: BrowserController, session_mgr: SessionManager) -> HumanHandoffService:
    return HumanHandoffService(
        controller=controller,
        session_manager=session_mgr,
        poll_interval_s=1,  # Fast polling for tests
    )


class TestHumanHandoffService:

    def test_build_request_returns_correct_model(
        self, handoff_service: HumanHandoffService
    ) -> None:
        req = handoff_service.build_request(
            platform=PlatformName.NAUKRI,
            reason="CAPTCHA detected",
            current_url="https://www.naukri.com/blocked",
        )
        assert req.platform == PlatformName.NAUKRI
        assert req.reason == "CAPTCHA detected"
        assert req.current_url == "https://www.naukri.com/blocked"
        assert req.timeout_seconds == 300  # default

    def test_build_request_with_custom_timeout(
        self, handoff_service: HumanHandoffService
    ) -> None:
        req = handoff_service.build_request(
            platform=PlatformName.LINKEDIN,
            reason="Auth wall",
            current_url="https://www.linkedin.com/authwall",
            timeout_seconds=60,
        )
        assert req.timeout_seconds == 60

    async def test_request_takeover_resolves_when_url_changes(
        self,
        controller: BrowserController,
        session_mgr: SessionManager,
        mock_browser: MagicMock,
    ) -> None:
        """Simulate user navigating away from blocked URL after 1 poll."""
        # First status call returns blocked URL, second returns resolved URL.
        call_count = 0
        original_status = controller.status

        def patched_status():
            nonlocal call_count
            call_count += 1
            from app.browser.schemas import BrowserStatus
            if call_count <= 1:
                return BrowserStatus(state=BrowserState.READY, current_url="https://www.naukri.com/blocked")
            return BrowserStatus(state=BrowserState.READY, current_url="https://www.naukri.com/jobs")

        controller.status = patched_status  # type: ignore[method-assign]

        # Ensure cookies are gettable for session snapshot.
        await controller.new_page()

        svc = HumanHandoffService(controller=controller, session_manager=session_mgr, poll_interval_s=1)
        req = svc.build_request(PlatformName.NAUKRI, "CAPTCHA", "https://www.naukri.com/blocked", timeout_seconds=10)
        result = await svc.request_takeover(req)

        assert result.resolved is True
        assert result.new_session_state == SessionState.AUTHENTICATED

    async def test_request_takeover_times_out(
        self,
        controller: BrowserController,
        session_mgr: SessionManager,
    ) -> None:
        """Simulate URL never changing — should time out."""
        # Status always returns the same blocked URL.
        from app.browser.schemas import BrowserStatus
        controller.status = lambda: BrowserStatus(  # type: ignore[method-assign]
            state=BrowserState.READY,
            current_url="https://www.naukri.com/blocked"
        )

        svc = HumanHandoffService(controller=controller, session_manager=session_mgr, poll_interval_s=1)
        req = svc.build_request(
            PlatformName.NAUKRI, "CAPTCHA", "https://www.naukri.com/blocked", timeout_seconds=3
        )
        result = await svc.request_takeover(req)

        assert result.resolved is False
        assert result.new_session_state == SessionState.CAPTCHA_REQUIRED

    async def test_on_challenge_detected_hook_called(
        self,
        controller: BrowserController,
        session_mgr: SessionManager,
    ) -> None:
        """Verify the hook is invoked when a challenge is passed."""
        hook_called_with = []

        async def hook(challenge: CaptchaChallenge):
            hook_called_with.append(challenge)

        from app.browser.schemas import BrowserStatus, CaptchaChallenge
        controller.status = lambda: BrowserStatus(  # type: ignore[method-assign]
            state=BrowserState.READY,
            current_url="https://www.naukri.com/blocked"
        )
        svc = HumanHandoffService(
            controller=controller,
            session_manager=session_mgr,
            poll_interval_s=1,
            on_challenge_detected=hook,
        )
        captcha = CaptchaChallenge(
            platform=PlatformName.NAUKRI,
            captcha_type=CaptchaType.RECAPTCHA_V2,
            current_url="https://www.naukri.com/blocked",
        )
        req = HumanTakeoverRequest(
            reason="Test",
            platform=PlatformName.NAUKRI,
            current_url="https://www.naukri.com/blocked",
            captcha_challenge=captcha,
            timeout_seconds=2,
        )
        await svc.request_takeover(req)
        assert len(hook_called_with) == 1
        assert hook_called_with[0].captcha_type == CaptchaType.RECAPTCHA_V2

    async def test_on_resolved_hook_called_after_resolution(
        self,
        controller: BrowserController,
        session_mgr: SessionManager,
    ) -> None:
        """Verify the resolved hook fires after successful resolution."""
        resolved_calls = []

        async def on_resolved(result: HumanTakeoverResult):
            resolved_calls.append(result)

        call_count = 0

        def patched_status():
            nonlocal call_count
            call_count += 1
            from app.browser.schemas import BrowserStatus
            if call_count <= 1:
                return BrowserStatus(state=BrowserState.READY, current_url="https://www.naukri.com/blocked")
            return BrowserStatus(state=BrowserState.READY, current_url="https://www.naukri.com/home")

        controller.status = patched_status  # type: ignore[method-assign]

        svc = HumanHandoffService(
            controller=controller,
            session_manager=session_mgr,
            poll_interval_s=1,
            on_resolved=on_resolved,
        )
        req = svc.build_request(PlatformName.NAUKRI, "test", "https://www.naukri.com/blocked", timeout_seconds=10)
        result = await svc.request_takeover(req)

        assert result.resolved is True
        assert len(resolved_calls) == 1

from app.browser.schemas import HumanTakeoverResult
