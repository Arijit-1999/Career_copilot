"""APP-002: Automation vs human-handoff router.

Inspects a JobApplication's current state (form mapping result, CAPTCHA signals,
platform-specific rules) and decides the appropriate AutomationLevel for the
next submission step.
"""

from __future__ import annotations

import uuid
from typing import List

from app.applications.enums import AutomationLevel
from app.applications.schemas import AutomationDecision


# ---------------------------------------------------------------------------
# Platform-level automation policies
# ---------------------------------------------------------------------------

#: Platforms that always require human login / SSO — automation cannot submit.
_ALWAYS_HUMAN_PLATFORMS: frozenset[str] = frozenset(
    {"linkedin", "workday", "greenhouse", "lever", "taleo", "icims"}
)

#: Platforms where partial-auto is the best we can offer (complex forms).
_PARTIAL_ONLY_PLATFORMS: frozenset[str] = frozenset(
    {"naukri", "indeed", "monster", "shine"}
)


def _normalise_platform(platform: str | None) -> str:
    return (platform or "").strip().lower()


class ApplicationRouter:
    """
    Decides whether an application step can be:
    - FULL_AUTO: bot safely submits without human review
    - PARTIAL_AUTO: bot fills form; human must confirm before submit
    - HUMAN_REQUIRED: platform/CAPTCHA/sensitive data blocks automation

    All signal sources are injected as plain data so the router stays
    side-effect-free and trivially testable.
    """

    def route(
        self,
        application_id: uuid.UUID,
        platform: str | None,
        automation_level_from_mapper: AutomationLevel,
        unmapped_required_fields: List[str],
        captcha_detected: bool = False,
        sso_detected: bool = False,
        previous_handoff_count: int = 0,
    ) -> AutomationDecision:
        """
        Evaluate all signals and return an AutomationDecision.

        Parameters
        ----------
        application_id:
            The UUID of the JobApplication being evaluated.
        platform:
            Platform name string (e.g. "linkedin", "naukri"). Case-insensitive.
        automation_level_from_mapper:
            Recommendation produced by the FormFieldMapper for this application.
        unmapped_required_fields:
            Required form fields the mapper could not fill.
        captcha_detected:
            True if a CAPTCHA challenge was detected on the page.
        sso_detected:
            True if an SSO / OAuth login gate was found.
        previous_handoff_count:
            Number of human handoffs already recorded for this application.
            If ≥ 2 we escalate to HUMAN_REQUIRED to avoid infinite retries.
        """
        blocking: List[str] = []
        norm_platform = _normalise_platform(platform)

        # 1. Hard blockers
        if captcha_detected:
            blocking.append("CAPTCHA detected — browser session needs human resolution")
        if sso_detected:
            blocking.append("SSO / OAuth gate detected — must authenticate manually")
        if norm_platform in _ALWAYS_HUMAN_PLATFORMS:
            blocking.append(
                f"Platform '{norm_platform}' requires human authentication or does not "
                "permit automated form submission"
            )
        if unmapped_required_fields:
            blocking.append(
                f"Required fields could not be mapped: {', '.join(unmapped_required_fields)}"
            )
        if previous_handoff_count >= 2:
            blocking.append(
                f"Application has already required {previous_handoff_count} human handoffs — "
                "escalating to HUMAN_REQUIRED to avoid loop"
            )
        if automation_level_from_mapper == AutomationLevel.HUMAN_REQUIRED:
            blocking.append(
                "Form mapper returned HUMAN_REQUIRED — unmapped sensitive or required fields present"
            )

        # 2. Determine final level
        if blocking:
            level = AutomationLevel.HUMAN_REQUIRED
            reason = "One or more blocking signals prevent full automation."
        elif (
            norm_platform in _PARTIAL_ONLY_PLATFORMS
            or automation_level_from_mapper == AutomationLevel.PARTIAL_AUTO
        ):
            level = AutomationLevel.PARTIAL_AUTO
            reason = (
                "Platform or form mapping requires human review before submission."
            )
        else:
            level = AutomationLevel.FULL_AUTO
            reason = "All signals clear — safe to automate end-to-end submission."

        return AutomationDecision(
            application_id=application_id,
            automation_level=level,
            reason=reason,
            blocking_signals=blocking,
            safe_to_proceed=(level == AutomationLevel.FULL_AUTO and not blocking),
        )
