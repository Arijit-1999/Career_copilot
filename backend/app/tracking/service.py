"""Business logic and analytics engine for Application Tracking and Feedback domain."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.applications.models import JobApplication
from app.applications.enums import ApplicationStatus
from app.jobs.models import Job
from app.candidate.models import CandidateSkill, CandidateProfile, Skill
from app.candidate.enums import SkillState
from app.matching.models import JobMatch
from app.tracking.models import (
    ApplicationTimelineEvent,
    ApplicationInterview,
    ApplicationOutcome,
)
from app.tracking.enums import (
    TimelineEventType,
    InterviewOutcome,
    RejectionCategory,
    OfferOutcome,
)
from app.tracking.schemas import (
    TimelineEventCreate,
    InterviewCreate,
    InterviewUpdate,
    OutcomeCreate,
    OutcomeUpdate,
    KanbanCardRead,
    KanbanColumn,
    KanbanBoardRead,
    FunnelStageMetric,
    FunnelAnalyticsRead,
    SkillGapTrend,
    SkillGapAnalyticsRead,
    ResponseTimeAnalyticsRead,
    MatchScoreOutcomeCorrelation,
    TrackingDashboardSummary,
)
from app.core.exceptions import EntityNotFoundException, ValidationException


class TrackingService:
    """Service handling lifecycle timeline logging, interview tracking, KanBan board, and analytics."""

    # -----------------------------------------------------------------------
    # Timeline Events (TRK-001)
    # -----------------------------------------------------------------------

    async def add_timeline_event(
        self,
        db: AsyncSession,
        application_id: uuid.UUID,
        payload: TimelineEventCreate,
    ) -> ApplicationTimelineEvent:
        """Log a new milestone or event to an application's chronological timeline."""
        app = await db.get(JobApplication, application_id)
        if not app:
            raise EntityNotFoundException(f"JobApplication {application_id} not found")

        event = ApplicationTimelineEvent(
            application_id=application_id,
            event_type=payload.event_type,
            title=payload.title,
            description=payload.description,
            from_status=payload.from_status,
            to_status=payload.to_status,
            event_timestamp=payload.event_timestamp or datetime.now(timezone.utc),
            extra_data=payload.extra_data,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    async def get_application_timeline(
        self,
        db: AsyncSession,
        application_id: uuid.UUID,
    ) -> List[ApplicationTimelineEvent]:
        """Fetch all chronological timeline events for a given application."""
        stmt = (
            select(ApplicationTimelineEvent)
            .where(ApplicationTimelineEvent.application_id == application_id)
            .order_by(asc(ApplicationTimelineEvent.event_timestamp))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # Interview Management (TRK-002)
    # -----------------------------------------------------------------------

    async def create_interview(
        self,
        db: AsyncSession,
        application_id: uuid.UUID,
        payload: InterviewCreate,
    ) -> ApplicationInterview:
        """Schedule or record an interview round and log a timeline event."""
        app = await db.get(JobApplication, application_id)
        if not app:
            raise EntityNotFoundException(f"JobApplication {application_id} not found")

        interview = ApplicationInterview(
            application_id=application_id,
            round_type=payload.round_type,
            round_number=payload.round_number,
            format=payload.format,
            scheduled_at=payload.scheduled_at,
            completed_at=payload.completed_at,
            interviewer_names=payload.interviewer_names,
            interviewer_titles=payload.interviewer_titles,
            meeting_link=payload.meeting_link,
            duration_minutes=payload.duration_minutes,
            preparation_notes=payload.preparation_notes,
            questions_asked=payload.questions_asked,
            feedback_received=payload.feedback_received,
            outcome=payload.outcome,
        )
        db.add(interview)

        # Automatically log a timeline milestone
        timeline_event = ApplicationTimelineEvent(
            application_id=application_id,
            event_type=TimelineEventType.INTERVIEW_SCHEDULED,
            title=f"Interview Scheduled: {payload.round_type.value.replace('_', ' ').title()} (Round {payload.round_number})",
            description=f"Format: {payload.format.value}, Scheduled: {payload.scheduled_at or 'TBD'}",
            event_timestamp=datetime.now(timezone.utc),
            extra_data={"round_type": payload.round_type.value, "format": payload.format.value},
        )
        db.add(timeline_event)

        # If application was in SCREENING or APPLIED, advance to INTERVIEWING
        if app.status in (ApplicationStatus.APPLIED, ApplicationStatus.SCREENING):
            app.status = ApplicationStatus.INTERVIEWING

        await db.commit()
        await db.refresh(interview)
        return interview

    async def get_application_interviews(
        self,
        db: AsyncSession,
        application_id: uuid.UUID,
    ) -> List[ApplicationInterview]:
        """Fetch all interview rounds for an application."""
        stmt = (
            select(ApplicationInterview)
            .where(ApplicationInterview.application_id == application_id)
            .order_by(asc(ApplicationInterview.round_number), asc(ApplicationInterview.scheduled_at))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_interview(
        self,
        db: AsyncSession,
        interview_id: uuid.UUID,
        payload: InterviewUpdate,
    ) -> ApplicationInterview:
        """Update interview round notes, schedule, or debrief outcome."""
        interview = await db.get(ApplicationInterview, interview_id)
        if not interview:
            raise EntityNotFoundException(f"ApplicationInterview {interview_id} not found")

        old_outcome = interview.outcome
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(interview, field, value)

        # If outcome changed to a resolved status, add timeline event
        if payload.outcome and payload.outcome != old_outcome:
            event_type = (
                TimelineEventType.INTERVIEW_COMPLETED
                if payload.outcome in (InterviewOutcome.PASSED, InterviewOutcome.FAILED, InterviewOutcome.AWAITING_FEEDBACK)
                else TimelineEventType.NOTE_ADDED
            )
            timeline_event = ApplicationTimelineEvent(
                application_id=interview.application_id,
                event_type=event_type,
                title=f"Interview Outcome: Round {interview.round_number} -> {payload.outcome.value}",
                description=interview.feedback_received or "Interview round outcome updated.",
                event_timestamp=datetime.now(timezone.utc),
                extra_data={"outcome": payload.outcome.value, "round_number": interview.round_number},
            )
            db.add(timeline_event)

        await db.commit()
        await db.refresh(interview)
        return interview

    # -----------------------------------------------------------------------
    # Outcome Logging (TRK-002)
    # -----------------------------------------------------------------------

    async def record_outcome(
        self,
        db: AsyncSession,
        application_id: uuid.UUID,
        payload: OutcomeCreate,
    ) -> ApplicationOutcome:
        """Record the terminal outcome (offer/rejection/withdrawn) for an application."""
        app = await db.get(JobApplication, application_id)
        if not app:
            raise EntityNotFoundException(f"JobApplication {application_id} not found")

        # Check for existing outcome
        stmt = select(ApplicationOutcome).where(ApplicationOutcome.application_id == application_id)
        res = await db.execute(stmt)
        existing = res.scalars().first()

        # Calculate response time days if created_at exists
        response_days = payload.response_time_days
        if response_days is None and app.created_at:
            now = datetime.now(timezone.utc)
            applied_dt = app.created_at if app.created_at.tzinfo else app.created_at.replace(tzinfo=timezone.utc)
            response_days = round((now - applied_dt).total_seconds() / 86400, 1)

        if existing:
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(existing, field, value)
            if response_days is not None:
                existing.response_time_days = response_days
            outcome = existing
        else:
            outcome = ApplicationOutcome(
                application_id=application_id,
                final_status=payload.final_status,
                rejection_category=payload.rejection_category,
                rejection_feedback=payload.rejection_feedback,
                offer_outcome=payload.offer_outcome,
                offer_salary_amount=payload.offer_salary_amount,
                offer_salary_currency=payload.offer_salary_currency,
                offer_equity=payload.offer_equity,
                offer_bonus=payload.offer_bonus,
                offer_deadline=payload.offer_deadline,
                lessons_learned=payload.lessons_learned,
                response_time_days=response_days,
            )
            db.add(outcome)

        # Sync application status
        app.status = payload.final_status

        # Add corresponding timeline event
        if payload.final_status == ApplicationStatus.OFFER:
            event_type = TimelineEventType.OFFER_RECEIVED
            title = f"Offer Received ({payload.offer_salary_currency or 'INR'} {payload.offer_salary_amount or 'Competitive'})"
        elif payload.final_status == ApplicationStatus.REJECTED:
            event_type = TimelineEventType.REJECTION_RECEIVED
            cat = f" - {payload.rejection_category.value}" if payload.rejection_category else ""
            title = f"Application Rejected{cat}"
        elif payload.final_status == ApplicationStatus.ACCEPTED:
            event_type = TimelineEventType.STATUS_CHANGED
            title = "Offer Accepted! 🎉"
        else:
            event_type = TimelineEventType.STATUS_CHANGED
            title = f"Outcome Logged: {payload.final_status.value}"

        timeline_event = ApplicationTimelineEvent(
            application_id=application_id,
            event_type=event_type,
            title=title,
            description=payload.rejection_feedback or payload.lessons_learned,
            event_timestamp=datetime.now(timezone.utc),
            extra_data={"final_status": payload.final_status.value},
        )
        db.add(timeline_event)

        await db.commit()
        await db.refresh(outcome)
        return outcome

    async def get_outcome(
        self,
        db: AsyncSession,
        application_id: uuid.UUID,
    ) -> Optional[ApplicationOutcome]:
        """Fetch outcome record for an application."""
        stmt = select(ApplicationOutcome).where(ApplicationOutcome.application_id == application_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    # -----------------------------------------------------------------------
    # KanBan Board Aggregator (TRK-001)
    # -----------------------------------------------------------------------

    async def get_kanban_board(
        self,
        db: AsyncSession,
        candidate_id: uuid.UUID,
    ) -> KanbanBoardRead:
        """Generate a KanBan board view with applications partitioned by lifecycle status."""
        stmt = (
            select(JobApplication)
            .options(
                selectinload(JobApplication.interviews),
                selectinload(JobApplication.timeline_events),
            )
            .where(JobApplication.candidate_id == candidate_id)
            .order_by(desc(JobApplication.updated_at))
        )
        result = await db.execute(stmt)
        applications = list(result.scalars().all())

        # Collect job IDs to fetch details & match scores in bulk
        job_ids = [app.job_id for app in applications if app.job_id]
        jobs_map: Dict[uuid.UUID, Job] = {}
        matches_map: Dict[uuid.UUID, float] = {}

        if job_ids:
            jobs_stmt = select(Job).where(Job.id.in_(job_ids))
            j_res = await db.execute(jobs_stmt)
            for j in j_res.scalars().all():
                jobs_map[j.id] = j

            matches_stmt = select(JobMatch).where(
                and_(
                    JobMatch.candidate_id == candidate_id,
                    JobMatch.job_id.in_(job_ids),
                )
            )
            m_res = await db.execute(matches_stmt)
            for m in m_res.scalars().all():
                matches_map[m.job_id] = m.overall_score

        # Status column definitions
        columns_config = [
            (ApplicationStatus.SAVED, "Saved / Wishlist"),
            (ApplicationStatus.PREPARING, "Preparing"),
            (ApplicationStatus.APPLYING, "Applying"),
            (ApplicationStatus.APPLIED, "Applied"),
            (ApplicationStatus.SCREENING, "Screening"),
            (ApplicationStatus.INTERVIEWING, "Interviewing"),
            (ApplicationStatus.OFFER, "Offers"),
            (ApplicationStatus.ACCEPTED, "Accepted"),
            (ApplicationStatus.REJECTED, "Rejected"),
            (ApplicationStatus.WITHDRAWN, "Withdrawn"),
        ]

        now = datetime.now(timezone.utc)
        column_cards: Dict[ApplicationStatus, List[KanbanCardRead]] = {
            status: [] for status, _ in columns_config
        }

        active_count = 0
        completed_count = 0

        for app in applications:
            job = jobs_map.get(app.job_id) if app.job_id else None
            match_score = matches_map.get(app.job_id) if app.job_id else None

            # Calculate days in stage
            updated_dt = app.updated_at if app.updated_at.tzinfo else app.updated_at.replace(tzinfo=timezone.utc)
            days_in_stage = max(0, (now - updated_dt).days)

            # Next upcoming interview
            upcoming = [
                i.scheduled_at
                for i in (app.interviews or [])
                if i.scheduled_at and i.outcome == InterviewOutcome.SCHEDULED
            ]
            next_interview = min(upcoming) if upcoming else None

            card = KanbanCardRead(
                application_id=app.id,
                candidate_id=app.candidate_id,
                job_id=app.job_id,
                job_title=job.title if job else None,
                company_name=job.company if job else None,
                platform=app.platform or (job.source.value if job and job.source else None),
                status=app.status,
                match_score=match_score,
                days_in_stage=days_in_stage,
                interview_count=len(app.interviews or []),
                next_interview_at=next_interview,
                timeline_event_count=len(app.timeline_events or []),
                applied_at=app.created_at,
                updated_at=app.updated_at,
            )

            if app.status in column_cards:
                column_cards[app.status].append(card)

            if app.status in (ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN):
                completed_count += 1
            else:
                active_count += 1

        columns: List[KanbanColumn] = []
        for status, label in columns_config:
            cards = column_cards[status]
            columns.append(
                KanbanColumn(
                    status=status,
                    label=label,
                    total_count=len(cards),
                    applications=cards,
                )
            )

        return KanbanBoardRead(
            candidate_id=candidate_id,
            total_active_applications=active_count,
            total_completed_applications=completed_count,
            columns=columns,
        )

    # -----------------------------------------------------------------------
    # Analytics Engine (TRK-003)
    # -----------------------------------------------------------------------

    async def get_funnel_analytics(
        self,
        db: AsyncSession,
        candidate_id: uuid.UUID,
    ) -> FunnelAnalyticsRead:
        """Compute recruitment conversion funnel statistics across all applications."""
        stmt = select(JobApplication.status, func.count(JobApplication.id)).where(
            JobApplication.candidate_id == candidate_id
        ).group_by(JobApplication.status)
        result = await db.execute(stmt)
        counts = {status: count for status, count in result.all()}

        total_discovered = counts.get(ApplicationStatus.DISCOVERED, 0)
        total_saved = counts.get(ApplicationStatus.SAVED, 0)
        total_applied = (
            counts.get(ApplicationStatus.APPLIED, 0)
            + counts.get(ApplicationStatus.SCREENING, 0)
            + counts.get(ApplicationStatus.INTERVIEWING, 0)
            + counts.get(ApplicationStatus.OFFER, 0)
            + counts.get(ApplicationStatus.ACCEPTED, 0)
            + counts.get(ApplicationStatus.REJECTED, 0)
            + counts.get(ApplicationStatus.WITHDRAWN, 0)
        )
        total_screening = (
            counts.get(ApplicationStatus.SCREENING, 0)
            + counts.get(ApplicationStatus.INTERVIEWING, 0)
            + counts.get(ApplicationStatus.OFFER, 0)
            + counts.get(ApplicationStatus.ACCEPTED, 0)
        )
        total_interviewing = (
            counts.get(ApplicationStatus.INTERVIEWING, 0)
            + counts.get(ApplicationStatus.OFFER, 0)
            + counts.get(ApplicationStatus.ACCEPTED, 0)
        )
        total_offers = (
            counts.get(ApplicationStatus.OFFER, 0)
            + counts.get(ApplicationStatus.ACCEPTED, 0)
        )
        total_accepted = counts.get(ApplicationStatus.ACCEPTED, 0)
        total_rejected = counts.get(ApplicationStatus.REJECTED, 0)
        total_withdrawn = counts.get(ApplicationStatus.WITHDRAWN, 0)

        applied_to_interview = round((total_interviewing / total_applied * 100), 1) if total_applied > 0 else 0.0
        applied_to_offer = round((total_offers / total_applied * 100), 1) if total_applied > 0 else 0.0

        stage_metrics: List[FunnelStageMetric] = [
            FunnelStageMetric(
                stage=ApplicationStatus.APPLIED,
                count=total_applied,
                conversion_from_applied_pct=100.0 if total_applied > 0 else 0.0,
                dropoff_count=total_applied - total_screening,
            ),
            FunnelStageMetric(
                stage=ApplicationStatus.SCREENING,
                count=total_screening,
                conversion_from_applied_pct=round((total_screening / total_applied * 100), 1) if total_applied > 0 else 0.0,
                dropoff_count=total_screening - total_interviewing,
            ),
            FunnelStageMetric(
                stage=ApplicationStatus.INTERVIEWING,
                count=total_interviewing,
                conversion_from_applied_pct=applied_to_interview,
                dropoff_count=total_interviewing - total_offers,
            ),
            FunnelStageMetric(
                stage=ApplicationStatus.OFFER,
                count=total_offers,
                conversion_from_applied_pct=applied_to_offer,
                dropoff_count=total_offers - total_accepted,
            ),
            FunnelStageMetric(
                stage=ApplicationStatus.ACCEPTED,
                count=total_accepted,
                conversion_from_applied_pct=round((total_accepted / total_applied * 100), 1) if total_applied > 0 else 0.0,
                dropoff_count=0,
            ),
        ]

        return FunnelAnalyticsRead(
            total_discovered=total_discovered,
            total_saved=total_saved,
            total_applied=total_applied,
            total_screening=total_screening,
            total_interviewing=total_interviewing,
            total_offers=total_offers,
            total_accepted=total_accepted,
            total_rejected=total_rejected,
            total_withdrawn=total_withdrawn,
            applied_to_interview_rate_pct=applied_to_interview,
            applied_to_offer_rate_pct=applied_to_offer,
            stages=stage_metrics,
        )

    async def get_skill_gap_analytics(
        self,
        db: AsyncSession,
        candidate_id: uuid.UUID,
    ) -> SkillGapAnalyticsRead:
        """Identify high-frequency missing skills in rejected vs applied jobs."""
        # Fetch candidate's verified skills
        c_stmt = (
            select(Skill.name)
            .join(CandidateSkill, Skill.id == CandidateSkill.skill_id)
            .where(
                and_(
                    CandidateSkill.candidate_id == candidate_id,
                    CandidateSkill.state == SkillState.VERIFIED,
                )
            )
        )
        c_res = await db.execute(c_stmt)
        candidate_skills = {s.lower().strip() for s in c_res.scalars().all()}

        # Fetch applications with jobs
        stmt = (
            select(JobApplication, Job)
            .join(Job, JobApplication.job_id == Job.id)
            .where(JobApplication.candidate_id == candidate_id)
        )
        res = await db.execute(stmt)
        rows = res.all()

        missing_in_rejected: Dict[str, int] = {}
        missing_in_applied: Dict[str, int] = {}
        total_rejections = 0
        total_applications = len(rows)

        for app, job in rows:
            is_rejected = app.status == ApplicationStatus.REJECTED
            if is_rejected:
                total_rejections += 1

            job_skills = [
                s.strip() for s in (job.required_skills or [])
                if s and s.strip()
            ]

            for skill in job_skills:
                skill_norm = skill.lower()
                if skill_norm not in candidate_skills:
                    missing_in_applied[skill] = missing_in_applied.get(skill, 0) + 1
                    if is_rejected:
                        missing_in_rejected[skill] = missing_in_rejected.get(skill, 0) + 1

        top_gaps: List[SkillGapTrend] = []
        for skill, count_app in missing_in_applied.items():
            count_rej = missing_in_rejected.get(skill, 0)
            denom = total_rejections if total_rejections > 0 else total_applications
            freq_pct = round((count_rej if total_rejections > 0 else count_app) / max(denom, 1) * 100, 1)

            priority = "HIGH" if freq_pct >= 40 else ("MEDIUM" if freq_pct >= 20 else "LOW")
            top_gaps.append(
                SkillGapTrend(
                    skill_name=skill,
                    missing_in_rejected_count=count_rej,
                    missing_in_applied_count=count_app,
                    impact_frequency_pct=freq_pct,
                    priority_level=priority,
                )
            )

        top_gaps.sort(key=lambda x: (x.missing_in_rejected_count, x.missing_in_applied_count), reverse=True)

        return SkillGapAnalyticsRead(
            candidate_id=candidate_id,
            total_rejections_analyzed=total_rejections,
            total_applications_analyzed=total_applications,
            top_skill_gaps=top_gaps[:10],
        )

    async def get_response_time_analytics(
        self,
        db: AsyncSession,
        candidate_id: uuid.UUID,
    ) -> ResponseTimeAnalyticsRead:
        """Compute average response velocity and ghosting rate."""
        stmt = (
            select(ApplicationOutcome.response_time_days, ApplicationOutcome.rejection_category)
            .join(JobApplication, ApplicationOutcome.application_id == JobApplication.id)
            .where(JobApplication.candidate_id == candidate_id)
        )
        res = await db.execute(stmt)
        outcomes = res.all()

        times = [o[0] for o in outcomes if o[0] is not None]
        avg_resp = round(sum(times) / len(times), 1) if times else None

        # Ghost rate
        ghost_count = sum(1 for o in outcomes if o[1] == RejectionCategory.GHOSTED_NO_RESPONSE)
        ghost_rate = round(ghost_count / len(outcomes) * 100, 1) if outcomes else 0.0

        return ResponseTimeAnalyticsRead(
            avg_days_to_first_response=avg_resp,
            avg_days_to_interview=avg_resp,
            avg_days_to_offer=avg_resp,
            avg_days_to_rejection=avg_resp,
            ghost_rate_pct=ghost_rate,
        )

    async def get_match_score_correlation(
        self,
        db: AsyncSession,
        candidate_id: uuid.UUID,
    ) -> MatchScoreOutcomeCorrelation:
        """Analyze correlation between AI match score and progression to interview/offer."""
        stmt = (
            select(JobMatch.overall_score, JobApplication.status)
            .join(JobApplication, and_(
                JobApplication.job_id == JobMatch.job_id,
                JobApplication.candidate_id == JobMatch.candidate_id,
            ))
            .where(JobApplication.candidate_id == candidate_id)
        )
        res = await db.execute(stmt)
        rows = res.all()

        all_scores = [r[0] for r in rows if r[0] is not None]
        interview_scores = [
            r[0] for r in rows
            if r[0] is not None and r[1] in (ApplicationStatus.INTERVIEWING, ApplicationStatus.OFFER, ApplicationStatus.ACCEPTED)
        ]
        offer_scores = [
            r[0] for r in rows
            if r[0] is not None and r[1] in (ApplicationStatus.OFFER, ApplicationStatus.ACCEPTED)
        ]
        rejected_scores = [
            r[0] for r in rows
            if r[0] is not None and r[1] == ApplicationStatus.REJECTED
        ]

        avg_all = round(sum(all_scores) / len(all_scores), 2) if all_scores else 0.0
        avg_int = round(sum(interview_scores) / len(interview_scores), 2) if interview_scores else None
        avg_off = round(sum(offer_scores) / len(offer_scores), 2) if offer_scores else None
        avg_rej = round(sum(rejected_scores) / len(rejected_scores), 2) if rejected_scores else None

        if avg_int and avg_rej:
            if avg_int > avg_rej:
                insight = f"Applications reaching interview have a +{round((avg_int - avg_rej)*100, 1)}% higher match score than rejections."
            else:
                insight = "Match scores are balanced across interview and rejection outcomes."
        else:
            insight = "Insufficient outcome data to evaluate match score correlation."

        return MatchScoreOutcomeCorrelation(
            avg_match_score_all=avg_all,
            avg_match_score_interviewed=avg_int,
            avg_match_score_offered=avg_off,
            avg_match_score_rejected=avg_rej,
            correlation_insight=insight,
        )

    async def get_dashboard_summary(
        self,
        db: AsyncSession,
        candidate_id: uuid.UUID,
    ) -> TrackingDashboardSummary:
        """Aggregate comprehensive tracking overview metrics."""
        candidate = await db.get(CandidateProfile, candidate_id)
        if not candidate:
            raise EntityNotFoundException(f"CandidateProfile {candidate_id} not found")

        funnel = await self.get_funnel_analytics(db, candidate_id)
        skill_gaps = await self.get_skill_gap_analytics(db, candidate_id)
        response_times = await self.get_response_time_analytics(db, candidate_id)
        correlation = await self.get_match_score_correlation(db, candidate_id)

        # Count active vs upcoming interviews
        stmt_int = (
            select(func.count(ApplicationInterview.id))
            .join(JobApplication, ApplicationInterview.application_id == JobApplication.id)
            .where(
                and_(
                    JobApplication.candidate_id == candidate_id,
                    ApplicationInterview.outcome == InterviewOutcome.SCHEDULED,
                )
            )
        )
        int_res = await db.execute(stmt_int)
        upcoming_interviews = int_res.scalar_one() or 0

        active_apps = funnel.total_applied - (funnel.total_accepted + funnel.total_rejected + funnel.total_withdrawn)

        return TrackingDashboardSummary(
            candidate_id=candidate_id,
            active_applications_count=max(0, active_apps),
            upcoming_interviews_count=upcoming_interviews,
            offers_count=funnel.total_offers,
            rejections_count=funnel.total_rejected,
            funnel=funnel,
            response_times=response_times,
            top_skill_gaps=skill_gaps.top_skill_gaps,
            match_score_correlation=correlation,
        )
