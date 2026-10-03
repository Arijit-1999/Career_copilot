"""Playwright browser controller with stealth headers and anti-detection.

This module provides a dependency-injectable wrapper around Playwright's
async API. Playwright is an *optional* dependency (listed under
``[project.optional-dependencies] browser``). The controller is designed
so that:

  1. Tests inject a mock page/browser via the constructor — no real browser
     binary is needed to run the test suite.
  2. Production use simply calls ``BrowserController.launch()`` which will
     import and start a real Playwright browser.
  3. Switching from mock to real requires zero refactoring.

Anti-detection techniques applied:
  - Randomised but realistic User-Agent strings (Chrome on Windows / Mac).
  - navigator.webdriver property hidden via init-script injection.
  - Randomised viewport ±10 px, locale, and timezone set.
  - Configurable slow-motion delay to mimic human pacing.
  - Accept-Language and sec-ch-ua headers set to match User-Agent.
"""

from __future__ import annotations

import random
import logging
from typing import Any, Optional, TYPE_CHECKING

from app.browser.enums import BrowserState
from app.browser.schemas import BrowserConfig, BrowserStatus

if TYPE_CHECKING:
    # Only imported for type hints so that tests without Playwright pass.
    from playwright.async_api import Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Realistic User-Agent Pool (Chrome on Windows & macOS)
# ---------------------------------------------------------------------------
_USER_AGENTS: list[str] = [
    # Chrome 122 / Windows 10
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Chrome 121 / Windows 11
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Chrome 122 / macOS Ventura
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Chrome 120 / macOS Sonoma
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# JavaScript injected before page scripts run to hide automation signals.
_STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { runtime: {} };
"""


class BrowserController:
    """Manages a single Playwright browser instance with stealth configuration.

    Usage (production)::

        async with BrowserController.launch(config) as ctrl:
            page = await ctrl.new_page()
            await page.goto("https://www.naukri.com")

    Usage (testing — inject mocks)::

        mock_browser = AsyncMock()
        ctrl = BrowserController(browser=mock_browser, config=BrowserConfig())
    """

    def __init__(
        self,
        browser: "Browser",
        config: Optional[BrowserConfig] = None,
    ) -> None:
        self._browser: "Browser" = browser
        self._config: BrowserConfig = config or BrowserConfig()
        self._context: Optional["BrowserContext"] = None
        self._state: BrowserState = BrowserState.IDLE
        self._current_url: Optional[str] = None
        self._user_agent: str = random.choice(_USER_AGENTS)

    # ------------------------------------------------------------------
    # Factory / context manager
    # ------------------------------------------------------------------

    @classmethod
    async def launch(cls, config: Optional[BrowserConfig] = None) -> "BrowserController":
        """Launch a real Playwright Chromium browser.

        Raises:
            ImportError: If the ``playwright`` package is not installed.
                         Install with: pip install 'career-copilot[browser]'
        """
        try:
            from playwright.async_api import async_playwright  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "Playwright is not installed. Run: pip install 'career-copilot[browser]' "
                "and then: playwright install chromium"
            ) from exc

        cfg = config or BrowserConfig()
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(
            headless=cfg.headless,
            slow_mo=cfg.slow_mo_ms,
        )
        logger.info("Playwright Chromium launched (headless=%s)", cfg.headless)
        return cls(browser=browser, config=cfg)

    async def __aenter__(self) -> "BrowserController":
        await self._ensure_context()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Core page management
    # ------------------------------------------------------------------

    async def _ensure_context(self) -> None:
        """Create or reuse the stealth browser context."""
        if self._context is not None:
            return

        self._state = BrowserState.LAUNCHING
        cfg = self._config

        # Randomise viewport slightly to avoid fingerprinting.
        width = cfg.viewport_width + random.randint(-10, 10)
        height = cfg.viewport_height + random.randint(-10, 10)

        stealth_headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            **cfg.extra_http_headers,
        }

        self._context = await self._browser.new_context(
            viewport={"width": width, "height": height},
            user_agent=self._user_agent,
            locale=cfg.locale,
            timezone_id=cfg.timezone_id,
            extra_http_headers=stealth_headers,
        )
        # Inject anti-detection script before every page load.
        await self._context.add_init_script(_STEALTH_INIT_SCRIPT)
        self._state = BrowserState.READY
        logger.info("Browser context ready (viewport=%dx%d, ua=%s...)", width, height, self._user_agent[:40])

    async def new_page(self) -> "Page":
        """Open and return a new stealth page in the current context."""
        await self._ensure_context()
        page = await self._context.new_page()  # type: ignore[union-attr]
        page.set_default_timeout(self._config.timeout_ms)
        return page

    async def navigate(self, page: "Page", url: str, wait_until: str = "domcontentloaded") -> None:
        """Navigate to ``url`` and track state."""
        self._state = BrowserState.NAVIGATING
        logger.info("Navigating to %s", url)
        await page.goto(url, wait_until=wait_until)
        self._current_url = url
        self._state = BrowserState.READY

    async def close(self) -> None:
        """Close the browser context and browser gracefully."""
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        try:
            await self._browser.close()
        except Exception:
            pass
        self._state = BrowserState.CLOSED
        logger.info("BrowserController closed.")

    # ------------------------------------------------------------------
    # Session cookie helpers
    # ------------------------------------------------------------------

    async def get_cookies(self) -> list[dict]:
        """Return all cookies in the current context."""
        if self._context is None:
            return []
        return await self._context.cookies()

    async def set_cookies(self, cookies: list[dict]) -> None:
        """Restore previously saved cookies into the current context."""
        await self._ensure_context()
        await self._context.add_cookies(cookies)  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> BrowserStatus:
        """Return a Pydantic snapshot of the current controller state."""
        return BrowserStatus(
            state=self._state,
            current_url=self._current_url,
        )
