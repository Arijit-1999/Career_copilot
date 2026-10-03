"""Human takeover and CAPTCHA handoff service (BRW-006).

When automation encounters a CAPTCHA or bot-detection challenge it cannot
solve automatically, this service:

  1. Pauses the automation loop and signals the user/operator.
  2. Optionally opens / focuses the browser window for manual resolution.
  3. Polls for resolution (DOM change / URL change) up to a configurable
     timeout.
  4. Resumes automation with the refreshed session state once resolved.
  5. Records the event so the session manager can update the stored profile.

Design:
  - The service is fully async and injectable (mock-friendly).
  - It does NOT open UI dialogs or send emails — that is left to a future
    notification layer. It exposes hooks (``on_challenge_detected``,
    ``on_resolved``) that callers can subscribe to.
  - Polling interval and maximum wait time are configurable.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional, TYPE_CHECKING

from app.browser.enums import PlatformName, SessionState
from app.browser.schemas import (
    CaptchaChallenge,
    HumanTakeoverRequest,
    HumanTakeoverResult,
    SessionSaveRequest,
)

if TYPE_CHECKING:
    from app.browser.controller import BrowserController
    from app.browser.session import SessionManager

logger = logging.getLogger("browser.handoff")

# Type alias for optional async hook callbacks.
ChallengeHook = Optional[Callable[[CaptchaChallenge], Awaitable[None]]]
ResolvedHook = Optional[Callable[[HumanTakeoverResult], Awaitable[None]]]

_DEFAULT_POLL_INTERVAL_S = 5   # How often to check for resolution.
_DEFAULT_TIMEOUT_S = 300       # Give up after 5 minutes by default.


class HumanHandoffService:
    """Manages human-in-the-loop takeover when automation is blocked.

    Parameters
    ----------
    controller:
        The active ``BrowserController`` instance.
    session_manager:
        The ``SessionManager`` used to snapshot session post-resolution.
    poll_interval_s:
        Seconds between resolution checks. Default: 5.
    on_challenge_detected:
        Optional async hook called when a challenge is first detected.
        Use this to send a notification, log to a tracking DB, etc.
    on_resolved:
        Optional async hook called when the challenge is resolved.
    """

    def __init__(
        self,
        controller: "BrowserController",
        session_manager: "SessionManager",
        poll_interval_s: int = _DEFAULT_POLL_INTERVAL_S,
        on_challenge_detected: ChallengeHook = None,
        on_resolved: ResolvedHook = None,
    ) -> None:
        self._ctrl = controller
        self._session_mgr = session_manager
        self._poll_interval = poll_interval_s
        self._on_challenge_detected = on_challenge_detected
        self._on_resolved = on_resolved

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def request_takeover(
        self,
        request: HumanTakeoverRequest,
        username: Optional[str] = None,
    ) -> HumanTakeoverResult:
        """Pause automation and wait for a human to resolve the challenge.

        Parameters
        ----------
        request:
            Describes why takeover is needed and how long to wait.
        username:
            If provided, the session manager will snapshot cookies after
            resolution and save them for future reuse.

        Returns
        -------
        HumanTakeoverResult
            ``resolved=True`` if the human solved the challenge within the
            timeout; ``resolved=False`` if the timeout expired.
        """
        logger.warning(
            "HUMAN TAKEOVER REQUESTED — platform=%s, reason=%s, url=%s",
            request.platform,
            request.reason,
            request.current_url,
        )

        # Fire the detection hook (e.g., send a desktop notification).
        if self._on_challenge_detected and request.captcha_challenge:
            try:
                await self._on_challenge_detected(request.captcha_challenge)
            except Exception as exc:
                logger.error("on_challenge_detected hook raised: %s", exc)

        # Poll until the URL changes (user navigated past the block)
        # or the timeout expires.
        resolved = await self._poll_for_resolution(
            blocked_url=request.current_url,
            timeout_s=request.timeout_seconds,
        )

        if not resolved:
            logger.error(
                "Takeover timed out after %ds — platform=%s",
                request.timeout_seconds,
                request.platform,
            )
            result = HumanTakeoverResult(
                resolved=False,
                new_session_state=SessionState.CAPTCHA_REQUIRED,
                notes=f"Timed out after {request.timeout_seconds}s.",
            )
            return result

        # Capture the current URL after resolution.
        status = self._ctrl.status()
        resumed_url = status.current_url or request.current_url

        # Snapshot the post-resolution session if username was provided.
        if username:
            await self._snapshot_session(request.platform, username)

        result = HumanTakeoverResult(
            resolved=True,
            resumed_url=resumed_url,
            new_session_state=SessionState.AUTHENTICATED,
            notes="Human resolved the challenge successfully.",
        )

        if self._on_resolved:
            try:
                await self._on_resolved(result)
            except Exception as exc:
                logger.error("on_resolved hook raised: %s", exc)

        logger.info(
            "Takeover resolved — platform=%s, resumed_url=%s",
            request.platform,
            resumed_url,
        )
        return result

    def build_request(
        self,
        platform: PlatformName,
        reason: str,
        current_url: str,
        captcha: Optional[CaptchaChallenge] = None,
        timeout_seconds: int = _DEFAULT_TIMEOUT_S,
    ) -> HumanTakeoverRequest:
        """Convenience factory for building a ``HumanTakeoverRequest``."""
        return HumanTakeoverRequest(
            reason=reason,
            platform=platform,
            current_url=current_url,
            captcha_challenge=captcha,
            timeout_seconds=timeout_seconds,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _poll_for_resolution(self, blocked_url: str, timeout_s: int) -> bool:
        """Poll the browser status until the URL changes from ``blocked_url``.

        Returns True as soon as the URL differs, False if timeout expires.
        """
        elapsed = 0
        logger.info(
            "Polling for resolution every %ds (max %ds) — blocked at %s",
            self._poll_interval,
            timeout_s,
            blocked_url,
        )
        while elapsed < timeout_s:
            await asyncio.sleep(self._poll_interval)
            elapsed += self._poll_interval

            status = self._ctrl.status()
            current_url = status.current_url or ""

            # Resolution detected when user navigates away from the challenge page.
            if current_url and current_url != blocked_url:
                logger.info(
                    "Resolution detected after %ds — new url=%s", elapsed, current_url
                )
                return True

            logger.debug("Still waiting for human… elapsed=%ds", elapsed)

        return False

    async def _snapshot_session(self, platform: PlatformName, username: str) -> None:
        """Capture current browser cookies and persist as a fresh session."""
        try:
            await self._session_mgr.capture_from_browser(
                controller=self._ctrl,
                platform=platform,
                username=username,
            )
            logger.info("Session snapshot saved for %s / %s after handoff.", platform, username[:4] + "***")
        except Exception as exc:
            logger.error("Session snapshot failed: %s", exc)
