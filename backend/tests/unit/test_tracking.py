"""Unit tests for the Application Tracking and Analytics domain."""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidate.models import CandidateProfile, CandidateSkill, Skill
from app.candidate.enums import SkillState
from app.jobs.models import Job
from app.jobs.enums import JobSourceType
from app.matching.models import JobMatch
from app.applications.models import JobApplication
from app.applications.enums import ApplicationStatus
from app.tracking.models import (
    ApplicationTimelineEvent,
    ApplicationInterview,
    ApplicationOutcome,
)
from app.tracking.enums import (
    TimelineEventType,
    InterviewRoundType,
    InterviewFormat,
    InterviewOutcome,
    RejectionCategory,
    OfferOutcome,
)
from app.tracking.schemas import (
    TimelineEventCreate,
    InterviewCreate,
    InterviewUpdate,
    OutcomeCreate,
)
from app.tracking.service import TrackingService
from app.core.exceptions import EntityNotFoundException


@pytest.fixture
def tracking_service() -> TrackingService:
    return TrackingService()


@pytest_asyncio.fixture
async def setup_candidate_and_job(db_session: AsyncSession):
    """Fixture providing a saved candidate, job listing, and initial application."""
    candidate = CandidateProfile(
        id=uuid.uuid4(),
        full_name="Jane Doe",
        email="jane.tracking@example.com",
    )
    db_session.add(candidate)

    # Add canonical skill and candidate skill
    canonical_skill = Skill(
        id=uuid.uuid4(),
        name="Python",
        canonical_name="python",
        category="Languages",
    )
    db_session.add(canonical_skill)

    cand_skill = CandidateSkill(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        skill_id=canonical_skill.id,
        state=SkillState.VERIFIED,
    )
    db_session.add(cand_skill)

    job = Job(
        id=uuid.uuid4(),
        title="Senior Python Engineer",
        normalized_title="senior python engineer",
        company="TechCorp",
        location="Remote",
        source=JobSourceType.LINKEDIN,
        source_job_id="test-job-999",
        description_raw="Senior Python Engineer job description with FastAPI and AWS.",
        description_clean="Senior Python Engineer job description with FastAPI and AWS.",
        content_hash="hash-test-tracking-job-999",
        required_skills=["Python", "FastAPI", "Kubernetes", "AWS"],
    )
    db_session.add(job)

    app = JobApplication(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        job_id=job.id,
        status=ApplicationStatus.APPLIED,
    )
    db_session.add(app)

    match = JobMatch(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        job_id=job.id,
        overall_score=88.0,
        skill_score=90.0,
        role_score=85.0,
        experience_score=90.0,
        location_score=100.0,
    )
    db_session.add(match)

    await db_session.commit()
    await db_session.refresh(candidate)
    await db_session.refresh(job)
    await db_session.refresh(app)
    return candidate, job, app


class TestTimelineEvents:

    async def test_add_timeline_event_success(
        self,
        db_session: AsyncSession,
        tracking_service: TrackingService,
        setup_candidate_and_job,
    ) -> None:
        _, _, app = setup_candidate_and_job

        payload = TimelineEventCreate(
            event_type=TimelineEventType.NOTE_ADDED,
            title="Recruiter reached out on LinkedIn",
            description="Recruiter asked for availability for a 30m screening call.",
        )
        event = await tracking_service.add_timeline_event(db_session, app.id, payload)

        assert event.id is not None
        assert event.application_id == app.id
        assert event.event_type == TimelineEventType.NOTE_ADDED
        assert event.title == "Recruiter reached out on LinkedIn"

    async def test_add_timeline_event_nonexistent_application_raises_404(
        self,
        db_session: AsyncSession,
        tracking_service: TrackingService,
    ) -> None:
        payload = TimelineEventCreate(
            event_type=TimelineEventType.NOTE_ADDED,
            title="Ghost Note",
        )
        with pytest.raises(EntityNotFoundException):
            await tracking_service.add_timeline_event(db_session, uuid.uuid4(), payload)

    async def test_get_application_timeline_chronological(
        self,
        db_session: AsyncSession,
        tracking_service: TrackingService,
        setup_candidate_and_job,
    ) -> None:
        _, _, app = setup_candidate_and_job

        t1 = datetime.now(timezone.utc) - timedelta(days=2)
        t2 = datetime.now(timezone.utc) - timedelta(days=1)

        await tracking_service.add_timeline_event(
            db_session,
            app.id,
            TimelineEventCreate(event_type=TimelineEventType.STATUS_CHANGED, title="First", event_timestamp=t1),
        )
        await tracking_service.add_timeline_event(
            db_session,
            app.id,
            TimelineEventCreate(event_type=TimelineEventType.STATUS_CHANGED, title="Second", event_timestamp=t2),
        )

        timeline = await tracking_service.get_application_timeline(db_session, app.id)
        assert len(timeline) >= 2
        assert timeline[0].title == "First"
        assert timeline[1].title == "Second"


class TestInterviewTracking:

    async def test_create_interview_promotes_status_and_logs_timeline(
        self,
        db_session: AsyncSession,
        tracking_service: TrackingService,
        setup_candidate_and_job,
    ) -> None:
        _, _, app = setup_candidate_and_job
        assert app.status == ApplicationStatus.APPLIED

        payload = InterviewCreate(
            round_type=InterviewRoundType.TECHNICAL_ROUND_1,
            round_number=1,
            format=InterviewFormat.VIDEO_CALL,
            scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
            interviewer_names="Alex Smith",
            interviewer_titles="Staff Backend Engineer",
            meeting_link="https://meet.google.com/abc-xyz",
            duration_minutes=60,
        )
        interview = await tracking_service.create_interview(db_session, app.id, payload)

        assert interview.id is not None
        assert interview.round_type == InterviewRoundType.TECHNICAL_ROUND_1
        assert interview.outcome == InterviewOutcome.SCHEDULED

        # Verify application status advanced to INTERVIEWING
        await db_session.refresh(app)
        assert app.status == ApplicationStatus.INTERVIEWING

        # Verify timeline event was auto-created
        timeline = await tracking_service.get_application_timeline(db_session, app.id)
        assert any(e.event_type == TimelineEventType.INTERVIEW_SCHEDULED for e in timeline)

    async def test_update_interview_logs_completion(
        self,
        db_session: AsyncSession,
        tracking_service: TrackingService,
        setup_candidate_and_job,
    ) -> None:
        _, _, app = setup_candidate_and_job

        create_payload = InterviewCreate(
            round_type=InterviewRoundType.RECRUITER_SCREEN,
            round_number=1,
        )
        interview = await tracking_service.create_interview(db_session, app.id, create_payload)

        update_payload = InterviewUpdate(
            outcome=InterviewOutcome.PASSED,
            feedback_received="Strong performance on Python and system design basics.",
        )
        updated = await tracking_service.update_interview(db_session, interview.id, update_payload)

        assert updated.outcome == InterviewOutcome.PASSED
        assert updated.feedback_received == "Strong performance on Python and system design basics."

        timeline = await tracking_service.get_application_timeline(db_session, app.id)
        assert any(e.event_type == TimelineEventType.INTERVIEW_COMPLETED for e in timeline)


class TestOutcomeRecording:

    async def test_record_offer_outcome(
        self,
        db_session: AsyncSession,
        tracking_service: TrackingService,
        setup_candidate_and_job,
    ) -> None:
        _, _, app = setup_candidate_and_job

        payload = OutcomeCreate(
            final_status=ApplicationStatus.OFFER,
            offer_outcome=OfferOutcome.PENDING_DECISION,
            offer_salary_amount=2800000.0,
            offer_salary_currency="INR",
            offer_equity="0.1% stock options",
            offer_bonus="10% annual performance bonus",
            lessons_learned="Tailoring resume to FastAPI and microservices led directly to interview.",
        )
        outcome = await tracking_service.record_outcome(db_session, app.id, payload)

        assert outcome.id is not None
        assert outcome.final_status == ApplicationStatus.OFFER
        assert outcome.offer_salary_amount == 2800000.0
        assert outcome.response_time_days is not None  # Auto calculated from applied_at

        await db_session.refresh(app)
        assert app.status == ApplicationStatus.OFFER

        # Check outcome retrieval
        fetched = await tracking_service.get_outcome(db_session, app.id)
        assert fetched is not None
        assert fetched.offer_salary_amount == 2800000.0

    async def test_record_rejection_outcome(
        self,
        db_session: AsyncSession,
        tracking_service: TrackingService,
        setup_candidate_and_job,
    ) -> None:
        _, _, app = setup_candidate_and_job

        payload = OutcomeCreate(
            final_status=ApplicationStatus.REJECTED,
            rejection_category=RejectionCategory.SKILLS_GAP,
            rejection_feedback="Required deeper experience in production Kubernetes.",
            lessons_learned="Need to build a hands-on K8s project.",
        )
        outcome = await tracking_service.record_outcome(db_session, app.id, payload)

        assert outcome.final_status == ApplicationStatus.REJECTED
        assert outcome.rejection_category == RejectionCategory.SKILLS_GAP

        await db_session.refresh(app)
        assert app.status == ApplicationStatus.REJECTED


class TestKanbanBoardAndAnalytics:

    async def test_get_kanban_board_partitioning(
        self,
        db_session: AsyncSession,
        tracking_service: TrackingService,
        setup_candidate_and_job,
    ) -> None:
        candidate, job, app = setup_candidate_and_job

        kanban = await tracking_service.get_kanban_board(db_session, candidate.id)

        assert kanban.candidate_id == candidate.id
        assert kanban.total_active_applications >= 1
        assert len(kanban.columns) == 10

        applied_col = next(c for c in kanban.columns if c.status == ApplicationStatus.APPLIED)
        assert applied_col.total_count == 1
        assert applied_col.applications[0].job_title == job.title
        assert applied_col.applications[0].match_score == 88.0

    async def test_funnel_and_skill_gap_analytics(
        self,
        db_session: AsyncSession,
        tracking_service: TrackingService,
        setup_candidate_and_job,
    ) -> None:
        candidate, _, app = setup_candidate_and_job

        # Reject application to test skill gap logic
        await tracking_service.record_outcome(
            db_session,
            app.id,
            OutcomeCreate(
                final_status=ApplicationStatus.REJECTED,
                rejection_category=RejectionCategory.SKILLS_GAP,
            ),
        )

        funnel = await tracking_service.get_funnel_analytics(db_session, candidate.id)
        assert funnel.total_applied == 1
        assert funnel.total_rejected == 1
        assert len(funnel.stages) == 5

        skill_gaps = await tracking_service.get_skill_gap_analytics(db_session, candidate.id)
        assert skill_gaps.candidate_id == candidate.id
        assert skill_gaps.total_rejections_analyzed == 1
        # FastAPI, Kubernetes, AWS are required by the job and missing from candidate verified skills
        missing_names = {g.skill_name for g in skill_gaps.top_skill_gaps}
        assert "Kubernetes" in missing_names or "AWS" in missing_names or "FastAPI" in missing_names

    async def test_dashboard_summary_aggregation(
        self,
        db_session: AsyncSession,
        tracking_service: TrackingService,
        setup_candidate_and_job,
    ) -> None:
        candidate, _, _ = setup_candidate_and_job

        dashboard = await tracking_service.get_dashboard_summary(db_session, candidate.id)
        assert dashboard.candidate_id == candidate.id
        assert dashboard.funnel is not None
        assert dashboard.response_times is not None
        assert dashboard.match_score_correlation is not None
