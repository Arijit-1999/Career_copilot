"""Persistent browser session manager.

Stores and restores authenticated browser sessions (cookies + storage)
to disk, so the user only needs to log in to each platform once.

Session profiles are saved as JSON files under a configurable directory
(default: ``<project_root>/.browser_sessions/``). Each file is named
``<platform>_<username_hash>.json``.

Design decisions:
  - Credentials (passwords) are NEVER stored. Only post-login session
    artifacts (cookies, local/session storage) are persisted.
  - The manager is synchronous for storage I/O but all Playwright calls
    it delegates remain async.
  - It is fully injectable: tests pass a tmp_path directory and mock
    controller instead of touching disk or a real browser.
"""

from __future__ import annotations

import json
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from app.browser.enums import PlatformName, SessionState
from app.browser.schemas import SessionProfile, SessionSaveRequest, SessionLoadResult

if TYPE_CHECKING:
    from app.browser.controller import BrowserController

logger = logging.getLogger(__name__)

_DEFAULT_SESSION_TTL_HOURS = 12  # Sessions older than this are treated as expired.


class SessionManager:
    """Manages persistent, reusable authenticated browser profiles.

    Usage (production)::

        mgr = SessionManager(sessions_dir=Path(".browser_sessions"))
        result = mgr.load_session(PlatformName.NAUKRI, username="user@example.com")
        if result.found and result.session_state == SessionState.AUTHENTICATED:
            await mgr.restore_to_browser(controller, PlatformName.NAUKRI, "user@example.com")

    Usage (testing)::

        mgr = SessionManager(sessions_dir=tmp_path)
        # All I/O goes to tmp_path — no shared state between tests.
    """

    def __init__(self, sessions_dir: Optional[Path] = None) -> None:
        self._dir: Path = sessions_dir or Path(".browser_sessions")
        self._dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _profile_path(self, platform: PlatformName, username: str) -> Path:
        """Deterministic file path for a (platform, username) pair."""
        username_hash = hashlib.sha256(username.encode()).hexdigest()[:12]
        return self._dir / f"{platform.value}_{username_hash}.json"

    @staticmethod
    def _is_expired(profile: SessionProfile) -> bool:
        """Return True if the session has passed its TTL or explicit expiry."""
        now = datetime.now(tz=timezone.utc)
        if profile.expires_at and profile.expires_at.replace(tzinfo=timezone.utc) < now:
            return True
        if profile.last_authenticated_at:
            last_auth = profile.last_authenticated_at
            if last_auth.tzinfo is None:
                last_auth = last_auth.replace(tzinfo=timezone.utc)
            if now - last_auth > timedelta(hours=_DEFAULT_SESSION_TTL_HOURS):
                return True
        return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_session(self, req: SessionSaveRequest) -> SessionProfile:
        """Persist session cookies and storage to disk."""
        profile = SessionProfile(
            platform=req.platform,
            username=req.username,
            state=SessionState.AUTHENTICATED,
            cookies=req.cookies,
            local_storage=req.local_storage,
            session_storage=req.session_storage,
            last_authenticated_at=datetime.now(tz=timezone.utc),
        )
        path = self._profile_path(req.platform, req.username)
        path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Session saved for %s / %s → %s", req.platform, req.username[:4] + "***", path.name)
        return profile

    def load_session(self, platform: PlatformName, username: str) -> SessionLoadResult:
        """Load a saved session from disk and check if it's still valid."""
        path = self._profile_path(platform, username)

        if not path.exists():
            logger.debug("No session file found for %s / %s", platform, username)
            return SessionLoadResult(found=False, platform=platform, session_state=SessionState.UNAUTHENTICATED)

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            profile = SessionProfile.model_validate(raw)
        except Exception as exc:
            logger.warning("Corrupt session file %s: %s", path.name, exc)
            path.unlink(missing_ok=True)
            return SessionLoadResult(found=False, platform=platform, session_state=SessionState.UNAUTHENTICATED)

        if self._is_expired(profile):
            logger.info("Session for %s expired — clearing.", platform)
            path.unlink(missing_ok=True)
            return SessionLoadResult(found=True, platform=platform, session_state=SessionState.EXPIRED, username=username)

        return SessionLoadResult(
            found=True,
            platform=platform,
            session_state=SessionState.AUTHENTICATED,
            username=username,
        )

    def delete_session(self, platform: PlatformName, username: str) -> bool:
        """Remove a stored session file. Returns True if it existed."""
        path = self._profile_path(platform, username)
        if path.exists():
            path.unlink()
            logger.info("Session deleted for %s / %s", platform, username[:4] + "***")
            return True
        return False

    async def restore_to_browser(
        self, controller: "BrowserController", platform: PlatformName, username: str
    ) -> bool:
        """Load saved cookies into the browser context.

        Returns:
            True  — cookies restored successfully.
            False — no valid session found.
        """
        path = self._profile_path(platform, username)
        if not path.exists():
            return False

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            profile = SessionProfile.model_validate(raw)
        except Exception as exc:
            logger.warning("Cannot restore session from %s: %s", path.name, exc)
            return False

        if self._is_expired(profile):
            logger.info("Session for %s expired — cannot restore.", platform)
            return False

        await controller.set_cookies(profile.cookies)
        logger.info("Restored %d cookies for %s", len(profile.cookies), platform)
        return True

    async def capture_from_browser(
        self, controller: "BrowserController", platform: PlatformName, username: str
    ) -> SessionProfile:
        """Snapshot current browser cookies and save as a new session."""
        cookies = await controller.get_cookies()
        req = SessionSaveRequest(
            platform=platform,
            username=username,
            cookies=cookies,
        )
        return self.save_session(req)
