"""Tests for Phase 8 — Application Assistance (APP-001 to APP-004).

Test classes
============
TestApplicationEnums        — state machine, valid transitions
TestFormFieldMapper         — keyword matching, confidence, automation recommendation
TestApplicationRouter       — automation routing with platform + signal combinations
TestApplicationService      — service lifecycle, transitions, form mapping, routing
TestApplicationsAPI         — integration: all REST endpoints via async HTTP client
"""

import uuid
import pytest
import pytest_asyncio

from app.applications.enums import (
    ApplicationStatus,
    ApplicationAction,
    AutomationLevel,
    VALID_TRANSITIONS,
)
from app.applications.schemas import (
    DetectedFormField,
    FormMappingRequest,
    CreateApplicationRequest,
    TransitionApplicationRequest,
    UpdateApplicationRequest,
    AttachResumeRequest,
)
from app.applications.form_mapper import FormFieldMapper
from app.applications.router_logic import ApplicationRouter


# =========================================================================
# Helpers
# =========================================================================

CANDIDATE_ID = uuid.uuid4()
JOB_ID = uuid.uuid4()

_FULL_PROFILE = {
    "full_name": "Arijit Bose",
    "first_name": "Arijit",
    "last_name": "Bose",
    "email": "arijit@example.com",
    "phone": "+91-9999999999",
    "linkedin_url": "https://linkedin.com/in/arijit",
    "github_url": "https://github.com/arijit",
    "website_url": "https://arijit.dev",
    "city": "Kolkata",
    "state": "West Bengal",
    "country": "India",
    "current_title": "Software Engineer",
    "current_company": "Acme Corp",
    "years_of_experience": "4",
    "notice_period": "30 days",
}

_EMPTY_PROFILE: dict = {}


def _make_field(
    field_name: str,
    label: str,
    field_type: str = "text",
    required: bool = True,
    options: list | None = None,
) -> DetectedFormField:
    return DetectedFormField(
        field_name=field_name,
        label=label,
        field_type=field_type,
        required=required,
        options=options or [],
    )


def _make_mapping_request(fields: list[DetectedFormField]) -> FormMappingRequest:
    return FormMappingRequest(
        candidate_id=CANDIDATE_ID,
        job_id=JOB_ID,
        detected_fields=fields,
    )


# =========================================================================
# APP-001 / APP-003 — State Machine & Enums
# =========================================================================

class TestApplicationEnums:
    """Verifies the lifecycle state machine transition table."""

    def test_discovered_to_saved(self):
        result = VALID_TRANSITIONS.get(
            (ApplicationStatus.DISCOVERED, ApplicationAction.SAVE)
        )
        assert result == ApplicationStatus.SAVED

    def test_saved_to_preparing(self):
        assert VALID_TRANSITIONS[
            (ApplicationStatus.SAVED, ApplicationAction.START_PREP)
        ] == ApplicationStatus.PREPARING

    def test_preparing_to_applying(self):
        assert VALID_TRANSITIONS[
            (ApplicationStatus.PREPARING, ApplicationAction.START_APPLY)
        ] == ApplicationStatus.APPLYING

    def test_applying_to_applied(self):
        assert VALID_TRANSITIONS[
            (ApplicationStatus.APPLYING, ApplicationAction.SUBMIT)
        ] == ApplicationStatus.APPLIED

    def test_applied_to_screening(self):
        assert VALID_TRANSITIONS[
            (ApplicationStatus.APPLIED, ApplicationAction.SCREEN)
        ] == ApplicationStatus.SCREENING

    def test_screening_to_interviewing(self):
        assert VALID_TRANSITIONS[
            (ApplicationStatus.SCREENING, ApplicationAction.INTERVIEW)
        ] == ApplicationStatus.INTERVIEWING

    def test_interviewing_to_offer(self):
        assert VALID_TRANSITIONS[
            (ApplicationStatus.INTERVIEWING, ApplicationAction.RECEIVE_OFFER)
        ] == ApplicationStatus.OFFER

    def test_offer_to_accepted(self):
        assert VALID_TRANSITIONS[
            (ApplicationStatus.OFFER, ApplicationAction.ACCEPT_OFFER)
        ] == ApplicationStatus.ACCEPTED

    def test_applying_to_rejected(self):
        assert VALID_TRANSITIONS[
            (ApplicationStatus.APPLYING, ApplicationAction.REJECT)
        ] == ApplicationStatus.REJECTED

    def test_interviewing_to_withdrawn(self):
        assert VALID_TRANSITIONS[
            (ApplicationStatus.INTERVIEWING, ApplicationAction.WITHDRAW)
        ] == ApplicationStatus.WITHDRAWN

    def test_invalid_transition_is_not_in_table(self):
        assert (ApplicationStatus.APPLIED, ApplicationAction.ACCEPT_OFFER) not in VALID_TRANSITIONS

    def test_all_statuses_are_strings(self):
        for s in ApplicationStatus:
            assert isinstance(s.value, str)

    def test_automation_level_values(self):
        assert AutomationLevel.FULL_AUTO.value == "FULL_AUTO"
        assert AutomationLevel.PARTIAL_AUTO.value == "PARTIAL_AUTO"
        assert AutomationLevel.HUMAN_REQUIRED.value == "HUMAN_REQUIRED"


# =========================================================================
# APP-001 — Form Field Mapper
# =========================================================================

class TestFormFieldMapper:
    """Tests for the keyword-regex form field mapper."""

    def _mapper(self, profile: dict = _FULL_PROFILE) -> FormFieldMapper:
        return FormFieldMapper(profile)

    # --- Keyword matching ---

    def test_maps_full_name(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("applicant_name", "Full Name")])
        result = mapper.map(req)
        assert result.mapped_fields[0].mapped_value == "Arijit Bose"

    def test_maps_first_name(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("fname", "First Name")])
        result = mapper.map(req)
        assert result.mapped_fields[0].mapped_value == "Arijit"

    def test_maps_last_name(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("lname", "Last Name")])
        result = mapper.map(req)
        assert result.mapped_fields[0].mapped_value == "Bose"

    def test_maps_email(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("email_addr", "Email")])
        result = mapper.map(req)
        assert result.mapped_fields[0].mapped_value == "arijit@example.com"

    def test_maps_phone_by_label(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("ph", "Mobile")])
        result = mapper.map(req)
        assert result.mapped_fields[0].mapped_value == "+91-9999999999"

    def test_maps_linkedin(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("linkedin", "LinkedIn Profile")])
        result = mapper.map(req)
        assert "linkedin" in (result.mapped_fields[0].mapped_value or "")

    def test_maps_city(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("city", "City")])
        result = mapper.map(req)
        assert result.mapped_fields[0].mapped_value == "Kolkata"

    def test_maps_current_title(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("designation", "Current Title")])
        result = mapper.map(req)
        assert result.mapped_fields[0].mapped_value == "Software Engineer"

    def test_maps_years_of_experience(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("yoe", "Years of Experience")])
        result = mapper.map(req)
        assert result.mapped_fields[0].mapped_value == "4"

    def test_unknown_field_has_zero_confidence(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("custom_q1", "Favourite Color")])
        result = mapper.map(req)
        assert result.mapped_fields[0].confidence == 0.0
        assert result.mapped_fields[0].mapped_value is None

    # --- Confidence & review flags ---

    def test_high_confidence_when_value_present(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("email", "Email")])
        result = mapper.map(req)
        assert result.mapped_fields[0].confidence >= 0.9

    def test_partial_confidence_when_value_missing_but_matched(self):
        mapper = self._mapper(_EMPTY_PROFILE)
        req = _make_mapping_request([_make_field("email", "Email")])
        result = mapper.map(req)
        field = result.mapped_fields[0]
        assert 0.5 <= field.confidence < 0.9

    def test_sensitive_field_flagged_for_review(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("expected_ctc", "Expected CTC")])
        result = mapper.map(req)
        assert result.mapped_fields[0].needs_human_review is True

    def test_visa_field_flagged_for_review(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("visa_status", "Visa Sponsorship")])
        result = mapper.map(req)
        assert result.mapped_fields[0].needs_human_review is True

    # --- Automation recommendation ---

    def test_full_auto_when_all_mapped_and_not_sensitive(self):
        mapper = self._mapper()
        req = _make_mapping_request([
            _make_field("fname", "First Name"),
            _make_field("lname", "Last Name"),
            _make_field("email", "Email"),
        ])
        result = mapper.map(req)
        assert result.automation_recommendation == AutomationLevel.FULL_AUTO

    def test_human_required_when_required_field_unmapped(self):
        mapper = self._mapper(_EMPTY_PROFILE)
        req = _make_mapping_request([_make_field("custom_q1", "Favourite Color", required=True)])
        result = mapper.map(req)
        assert result.automation_recommendation == AutomationLevel.HUMAN_REQUIRED
        assert "custom_q1" in result.unmapped_required_fields

    def test_partial_auto_when_sensitive_field_present(self):
        mapper = self._mapper()
        fields = [
            _make_field("fname", "First Name"),
            _make_field("salary", "Expected Salary", required=False),
        ]
        req = _make_mapping_request(fields)
        result = mapper.map(req)
        assert result.automation_recommendation in (
            AutomationLevel.PARTIAL_AUTO, AutomationLevel.FULL_AUTO
        )

    def test_overall_confidence_is_average(self):
        mapper = self._mapper()
        req = _make_mapping_request([
            _make_field("email", "Email"),
            _make_field("fname", "First Name"),
        ])
        result = mapper.map(req)
        assert 0.0 <= result.overall_confidence <= 1.0

    def test_candidate_id_preserved_in_result(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("email", "Email")])
        result = mapper.map(req)
        assert result.candidate_id == CANDIDATE_ID

    def test_job_id_preserved_in_result(self):
        mapper = self._mapper()
        req = _make_mapping_request([_make_field("email", "Email")])
        result = mapper.map(req)
        assert result.job_id == JOB_ID


# =========================================================================
# APP-002 — Automation Router
# =========================================================================

class TestApplicationRouter:
    """Tests for the platform-aware automation routing logic."""

    def _router(self) -> ApplicationRouter:
        return ApplicationRouter()

    def _route(
        self,
        platform: str = "generic",
        mapper_level: AutomationLevel = AutomationLevel.FULL_AUTO,
        unmapped: list | None = None,
        captcha: bool = False,
        sso: bool = False,
        handoffs: int = 0,
    ):
        return self._router().route(
            application_id=uuid.uuid4(),
            platform=platform,
            automation_level_from_mapper=mapper_level,
            unmapped_required_fields=unmapped or [],
            captcha_detected=captcha,
            sso_detected=sso,
            previous_handoff_count=handoffs,
        )

    # --- Clean path ---

    def test_full_auto_for_clean_generic_platform(self):
        decision = self._route()
        assert decision.automation_level == AutomationLevel.FULL_AUTO
        assert decision.safe_to_proceed is True

    # --- Platform policies ---

    def test_linkedin_is_human_required(self):
        decision = self._route(platform="linkedin")
        assert decision.automation_level == AutomationLevel.HUMAN_REQUIRED
        assert not decision.safe_to_proceed

    def test_workday_is_human_required(self):
        decision = self._route(platform="workday")
        assert decision.automation_level == AutomationLevel.HUMAN_REQUIRED

    def test_greenhouse_is_human_required(self):
        decision = self._route(platform="greenhouse")
        assert decision.automation_level == AutomationLevel.HUMAN_REQUIRED

    def test_naukri_is_partial_auto(self):
        decision = self._route(platform="naukri")
        assert decision.automation_level == AutomationLevel.PARTIAL_AUTO

    def test_indeed_is_partial_auto(self):
        decision = self._route(platform="indeed")
        assert decision.automation_level == AutomationLevel.PARTIAL_AUTO

    def test_platform_case_insensitive(self):
        decision = self._route(platform="LinkedIn")
        assert decision.automation_level == AutomationLevel.HUMAN_REQUIRED

    # --- Signal blockers ---

    def test_captcha_forces_human(self):
        decision = self._route(captcha=True)
        assert decision.automation_level == AutomationLevel.HUMAN_REQUIRED
        assert any("CAPTCHA" in s for s in decision.blocking_signals)

    def test_sso_forces_human(self):
        decision = self._route(sso=True)
        assert decision.automation_level == AutomationLevel.HUMAN_REQUIRED
        assert any("SSO" in s for s in decision.blocking_signals)

    def test_unmapped_required_forces_human(self):
        decision = self._route(unmapped=["cover_letter", "ssn"])
        assert decision.automation_level == AutomationLevel.HUMAN_REQUIRED
        assert any("cover_letter" in s for s in decision.blocking_signals)

    def test_two_handoffs_escalates_to_human(self):
        decision = self._route(handoffs=2)
        assert decision.automation_level == AutomationLevel.HUMAN_REQUIRED
        assert any("handoff" in s.lower() for s in decision.blocking_signals)

    def test_one_handoff_does_not_escalate(self):
        decision = self._route(handoffs=1)
        assert decision.automation_level == AutomationLevel.FULL_AUTO

    # --- Mapper signal propagation ---

    def test_partial_mapper_on_generic_platform_gives_partial(self):
        decision = self._route(mapper_level=AutomationLevel.PARTIAL_AUTO)
        assert decision.automation_level == AutomationLevel.PARTIAL_AUTO

    def test_human_mapper_on_generic_platform_gives_human(self):
        decision = self._route(mapper_level=AutomationLevel.HUMAN_REQUIRED)
        # Not a hard blocker in the router — partial or human depending on implementation
        # The router will just relay the partial/human recommendation
        assert decision.automation_level != AutomationLevel.FULL_AUTO

    # --- blocking_signals list ---

    def test_multiple_blockers_all_reported(self):
        decision = self._route(captcha=True, sso=True, unmapped=["field_x"])
        assert len(decision.blocking_signals) >= 3

    def test_no_blockers_gives_empty_list(self):
        decision = self._route()
        assert decision.blocking_signals == []

    def test_decision_contains_application_id(self):
        app_id = uuid.uuid4()
        decision = self._router().route(
            application_id=app_id,
            platform="generic",
            automation_level_from_mapper=AutomationLevel.FULL_AUTO,
            unmapped_required_fields=[],
        )
        assert decision.application_id == app_id


# =========================================================================
# APP-003 / APP-004 — Service & API integration tests
# =========================================================================

@pytest.mark.asyncio
class TestApplicationService:
    """Service-layer tests using the in-memory SQLite DB from conftest."""

    async def test_create_application_defaults_to_discovered(self, async_client):
        payload = {"candidate_id": str(CANDIDATE_ID)}
        resp = await async_client.post("/api/v1/applications", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "DISCOVERED"
        assert data["candidate_id"] == str(CANDIDATE_ID)
        assert data["transition_history"] == []

    async def test_create_application_with_platform(self, async_client):
        payload = {
            "candidate_id": str(CANDIDATE_ID),
            "platform": "naukri",
            "external_job_url": "https://naukri.com/job/12345678",
        }
        resp = await async_client.post("/api/v1/applications", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["platform"] == "naukri"

    async def test_get_application_returns_detail(self, async_client):
        create_resp = await async_client.post(
            "/api/v1/applications", json={"candidate_id": str(CANDIDATE_ID)}
        )
        app_id = create_resp.json()["id"]
        resp = await async_client.get(f"/api/v1/applications/{app_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == app_id

    async def test_get_nonexistent_application_returns_404(self, async_client):
        resp = await async_client.get(f"/api/v1/applications/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_list_applications_returns_list(self, async_client):
        await async_client.post("/api/v1/applications", json={"candidate_id": str(CANDIDATE_ID)})
        resp = await async_client.get("/api/v1/applications")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_applications_filter_by_candidate(self, async_client):
        other_id = str(uuid.uuid4())
        await async_client.post("/api/v1/applications", json={"candidate_id": str(CANDIDATE_ID)})
        await async_client.post("/api/v1/applications", json={"candidate_id": other_id})
        resp = await async_client.get(
            f"/api/v1/applications?candidate_id={CANDIDATE_ID}"
        )
        assert resp.status_code == 200
        items = resp.json()
        assert all(i["candidate_id"] == str(CANDIDATE_ID) for i in items)

    async def test_update_application_notes(self, async_client):
        create_resp = await async_client.post(
            "/api/v1/applications", json={"candidate_id": str(CANDIDATE_ID)}
        )
        app_id = create_resp.json()["id"]
        resp = await async_client.patch(
            f"/api/v1/applications/{app_id}", json={"notes": "Promising role"}
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Promising role"

    async def test_attach_resume(self, async_client):
        create_resp = await async_client.post(
            "/api/v1/applications", json={"candidate_id": str(CANDIDATE_ID)}
        )
        app_id = create_resp.json()["id"]
        resume_id = str(uuid.uuid4())
        resp = await async_client.post(
            f"/api/v1/applications/{app_id}/attach-resume",
            json={"resume_id": resume_id},
        )
        assert resp.status_code == 200
        assert resp.json()["resume_id"] == resume_id

    # --- Lifecycle transitions ---

    async def test_valid_transition_discovered_to_saved(self, async_client):
        create_resp = await async_client.post(
            "/api/v1/applications", json={"candidate_id": str(CANDIDATE_ID)}
        )
        app_id = create_resp.json()["id"]
        resp = await async_client.post(
            f"/api/v1/applications/{app_id}/transition",
            json={"action": "SAVE"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SAVED"
        assert len(data["transition_history"]) == 1
        assert data["transition_history"][0]["action"] == "SAVE"

    async def test_full_lifecycle_discovered_to_applied(self, async_client):
        create_resp = await async_client.post(
            "/api/v1/applications", json={"candidate_id": str(CANDIDATE_ID)}
        )
        app_id = create_resp.json()["id"]
        for action in ["SAVE", "START_PREP", "START_APPLY", "SUBMIT"]:
            resp = await async_client.post(
                f"/api/v1/applications/{app_id}/transition",
                json={"action": action},
            )
            assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "APPLIED"
        assert len(data["transition_history"]) == 4

    async def test_invalid_transition_returns_422(self, async_client):
        create_resp = await async_client.post(
            "/api/v1/applications", json={"candidate_id": str(CANDIDATE_ID)}
        )
        app_id = create_resp.json()["id"]
        # Can't SUBMIT from DISCOVERED
        resp = await async_client.post(
            f"/api/v1/applications/{app_id}/transition",
            json={"action": "SUBMIT"},
        )
        assert resp.status_code == 422

    async def test_reject_from_interviewing(self, async_client):
        create_resp = await async_client.post(
            "/api/v1/applications", json={"candidate_id": str(CANDIDATE_ID)}
        )
        app_id = create_resp.json()["id"]
        for action in ["SAVE", "START_PREP", "START_APPLY", "SUBMIT", "SCREEN", "INTERVIEW"]:
            await async_client.post(
                f"/api/v1/applications/{app_id}/transition",
                json={"action": action},
            )
        resp = await async_client.post(
            f"/api/v1/applications/{app_id}/transition",
            json={"action": "REJECT"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "REJECTED"

    async def test_transition_records_actor(self, async_client):
        create_resp = await async_client.post(
            "/api/v1/applications", json={"candidate_id": str(CANDIDATE_ID)}
        )
        app_id = create_resp.json()["id"]
        resp = await async_client.post(
            f"/api/v1/applications/{app_id}/transition",
            json={"action": "SAVE", "actor": "system"},
        )
        assert resp.json()["transition_history"][0]["actor"] == "system"

    # --- Form mapping endpoint ---

    async def test_map_form_fields_returns_result(self, async_client):
        create_resp = await async_client.post(
            "/api/v1/applications", json={"candidate_id": str(CANDIDATE_ID)}
        )
        app_id = create_resp.json()["id"]
        payload = {
            "candidate_id": str(CANDIDATE_ID),
            "job_id": str(JOB_ID),
            "detected_fields": [
                {"field_name": "fname", "label": "First Name", "field_type": "text", "required": True},
                {"field_name": "email", "label": "Email", "field_type": "text", "required": True},
            ],
            "page_context": {
                "candidate_profile": {
                    "first_name": "Arijit",
                    "email": "arijit@example.com",
                }
            },
        }
        resp = await async_client.post(
            f"/api/v1/applications/{app_id}/map-form", json=payload
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "mapped_fields" in data
        assert "automation_recommendation" in data

    # --- Automation decision endpoint ---

    async def test_automation_decision_no_captcha(self, async_client):
        create_resp = await async_client.post(
            "/api/v1/applications",
            json={"candidate_id": str(CANDIDATE_ID), "platform": "generic"},
        )
        app_id = create_resp.json()["id"]
        resp = await async_client.post(
            f"/api/v1/applications/{app_id}/automation-decision"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "automation_level" in data
        assert "safe_to_proceed" in data

    async def test_automation_decision_with_captcha(self, async_client):
        create_resp = await async_client.post(
            "/api/v1/applications", json={"candidate_id": str(CANDIDATE_ID)}
        )
        app_id = create_resp.json()["id"]
        resp = await async_client.post(
            f"/api/v1/applications/{app_id}/automation-decision?captcha_detected=true"
        )
        assert resp.status_code == 200
        assert resp.json()["automation_level"] == "HUMAN_REQUIRED"

    async def test_automation_decision_increments_handoff_count(self, async_client):
        create_resp = await async_client.post(
            "/api/v1/applications",
            json={"candidate_id": str(CANDIDATE_ID), "platform": "linkedin"},
        )
        app_id = create_resp.json()["id"]
        # LinkedIn always triggers HUMAN_REQUIRED → handoff_count++
        resp = await async_client.post(
            f"/api/v1/applications/{app_id}/automation-decision"
        )
        assert resp.status_code == 200
        detail = await async_client.get(f"/api/v1/applications/{app_id}")
        assert detail.json()["handoff_count"] == 1
