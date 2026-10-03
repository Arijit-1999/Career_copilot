"""Enumerations for the Application Assistance domain."""

from enum import Enum


class ApplicationStatus(str, Enum):
    """Lifecycle states for a tracked job application."""

    DISCOVERED = "DISCOVERED"          # Job found, no action taken yet
    SAVED = "SAVED"                    # Candidate manually saved for later
    PREPARING = "PREPARING"            # Resume / cover letter being tailored
    APPLYING = "APPLYING"              # Automation or human in the process of submitting
    APPLIED = "APPLIED"                # Form successfully submitted
    SCREENING = "SCREENING"            # Recruiter phone/assessment stage
    INTERVIEWING = "INTERVIEWING"      # One or more interview rounds scheduled
    OFFER = "OFFER"                    # Offer received
    ACCEPTED = "ACCEPTED"              # Offer accepted by candidate
    REJECTED = "REJECTED"              # Rejected at any stage
    WITHDRAWN = "WITHDRAWN"            # Candidate withdrew application


class ApplicationAction(str, Enum):
    """User-triggered or automation-triggered transitions."""

    SAVE = "SAVE"                      # DISCOVERED → SAVED
    START_PREP = "START_PREP"          # SAVED → PREPARING
    START_APPLY = "START_APPLY"        # PREPARING → APPLYING
    SUBMIT = "SUBMIT"                  # APPLYING → APPLIED
    SCREEN = "SCREEN"                  # APPLIED → SCREENING
    INTERVIEW = "INTERVIEW"            # SCREENING → INTERVIEWING
    RECEIVE_OFFER = "RECEIVE_OFFER"    # INTERVIEWING → OFFER
    ACCEPT_OFFER = "ACCEPT_OFFER"      # OFFER → ACCEPTED
    REJECT = "REJECT"                  # Any → REJECTED
    WITHDRAW = "WITHDRAW"              # Any → WITHDRAWN


class AutomationLevel(str, Enum):
    """Whether a step can be automated or requires human action."""

    FULL_AUTO = "FULL_AUTO"            # Safe to automate end-to-end
    PARTIAL_AUTO = "PARTIAL_AUTO"      # Automation fills form; human reviews before submit
    HUMAN_REQUIRED = "HUMAN_REQUIRED"  # CAPTCHA, SSO, or complex step; must hand off


# ---------------------------------------------------------------------------
# State-machine: valid transitions
# ---------------------------------------------------------------------------

#: Maps each (current_status, action) pair to the resulting status.
VALID_TRANSITIONS: dict[tuple[ApplicationStatus, ApplicationAction], ApplicationStatus] = {
    (ApplicationStatus.DISCOVERED,  ApplicationAction.SAVE):         ApplicationStatus.SAVED,
    (ApplicationStatus.SAVED,       ApplicationAction.START_PREP):   ApplicationStatus.PREPARING,
    (ApplicationStatus.PREPARING,   ApplicationAction.START_APPLY):  ApplicationStatus.APPLYING,
    (ApplicationStatus.APPLYING,    ApplicationAction.SUBMIT):       ApplicationStatus.APPLIED,
    (ApplicationStatus.APPLIED,     ApplicationAction.SCREEN):       ApplicationStatus.SCREENING,
    (ApplicationStatus.SCREENING,   ApplicationAction.INTERVIEW):    ApplicationStatus.INTERVIEWING,
    (ApplicationStatus.INTERVIEWING,ApplicationAction.RECEIVE_OFFER):ApplicationStatus.OFFER,
    (ApplicationStatus.OFFER,       ApplicationAction.ACCEPT_OFFER): ApplicationStatus.ACCEPTED,
    # Reject/withdraw allowed from most active states
    (ApplicationStatus.SAVED,       ApplicationAction.REJECT):       ApplicationStatus.REJECTED,
    (ApplicationStatus.PREPARING,   ApplicationAction.REJECT):       ApplicationStatus.REJECTED,
    (ApplicationStatus.APPLYING,    ApplicationAction.REJECT):       ApplicationStatus.REJECTED,
    (ApplicationStatus.APPLIED,     ApplicationAction.REJECT):       ApplicationStatus.REJECTED,
    (ApplicationStatus.SCREENING,   ApplicationAction.REJECT):       ApplicationStatus.REJECTED,
    (ApplicationStatus.INTERVIEWING,ApplicationAction.REJECT):       ApplicationStatus.REJECTED,
    (ApplicationStatus.OFFER,       ApplicationAction.REJECT):       ApplicationStatus.REJECTED,
    (ApplicationStatus.SAVED,       ApplicationAction.WITHDRAW):     ApplicationStatus.WITHDRAWN,
    (ApplicationStatus.PREPARING,   ApplicationAction.WITHDRAW):     ApplicationStatus.WITHDRAWN,
    (ApplicationStatus.APPLYING,    ApplicationAction.WITHDRAW):     ApplicationStatus.WITHDRAWN,
    (ApplicationStatus.APPLIED,     ApplicationAction.WITHDRAW):     ApplicationStatus.WITHDRAWN,
    (ApplicationStatus.SCREENING,   ApplicationAction.WITHDRAW):     ApplicationStatus.WITHDRAWN,
    (ApplicationStatus.INTERVIEWING,ApplicationAction.WITHDRAW):     ApplicationStatus.WITHDRAWN,
    (ApplicationStatus.OFFER,       ApplicationAction.WITHDRAW):     ApplicationStatus.WITHDRAWN,
}
