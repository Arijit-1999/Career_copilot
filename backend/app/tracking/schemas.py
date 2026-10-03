"""Pydantic v2 schemas for the Tracking & Analytics domain."""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from app.applications.enums import ApplicationStatus
from app.tracking.enums import (
    TimelineEventType,
    InterviewRoundType,
    InterviewFormat,
    InterviewOutcome,
    RejectionCategory,
    OfferOutcome,
)


# ---------------------------------------------------------------------------
# Timeline Event Schemas
# ---------------------------------------------------------------------------

class TimelineEventCreate(BaseModel):
    """Payload to log a new chronological event on an application."""
    event_type: TimelineEventType
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    event_timestamp: Optional[datetime] = None
    extra_data: Dict[str, Any] = Field(default_factory=dict)


class TimelineEventRead(BaseModel):
    """Representation of an existing timeline event."""
    id: uuid.UUID
    application_id: uuid.UUID
    event_type: TimelineEventType
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    title: str
    description: Optional[str] = None
    event_timestamp: datetime
    extra_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Interview Schemas
# ---------------------------------------------------------------------------

class InterviewCreate(BaseModel):
    """Payload to schedule or record an interview round."""
    round_type: InterviewRoundType = InterviewRoundType.RECRUITER_SCREEN
    round_number: int = Field(default=1, ge=1)
    format: InterviewFormat = InterviewFormat.VIDEO_CALL
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    interviewer_names: Optional[str] = None
    interviewer_titles: Optional[str] = None
    meeting_link: Optional[str] = None
    duration_minutes: Optional[int] = Field(default=45, ge=5, le=480)
    preparation_notes: Optional[str] = None
    questions_asked: Optional[str] = None
    feedback_received: Optional[str] = None
    outcome: InterviewOutcome = InterviewOutcome.SCHEDULED


class InterviewUpdate(BaseModel):
    """Payload to update an interview round's notes, outcome, or schedule."""
    round_type: Optional[InterviewRoundType] = None
    round_number: Optional[int] = None
    format: Optional[InterviewFormat] = None
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    interviewer_names: Optional[str] = None
    interviewer_titles: Optional[str] = None
    meeting_link: Optional[str] = None
    duration_minutes: Optional[int] = None
    preparation_notes: Optional[str] = None
    questions_asked: Optional[str] = None
    feedback_received: Optional[str] = None
    outcome: Optional[InterviewOutcome] = None


class InterviewRead(BaseModel):
    """Representation of an interview round record."""
    id: uuid.UUID
    application_id: uuid.UUID
    round_type: InterviewRoundType
    round_number: int
    format: InterviewFormat
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    interviewer_names: Optional[str] = None
    interviewer_titles: Optional[str] = None
    meeting_link: Optional[str] = None
    duration_minutes: Optional[int] = None
    preparation_notes: Optional[str] = None
    questions_asked: Optional[str] = None
    feedback_received: Optional[str] = None
    outcome: InterviewOutcome
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Outcome Schemas
# ---------------------------------------------------------------------------

class OutcomeCreate(BaseModel):
    """Payload to record the final outcome of an application."""
    final_status: ApplicationStatus
    rejection_category: Optional[RejectionCategory] = None
    rejection_feedback: Optional[str] = None
    offer_outcome: Optional[OfferOutcome] = None
    offer_salary_amount: Optional[float] = None
    offer_salary_currency: Optional[str] = "INR"
    offer_equity: Optional[str] = None
    offer_bonus: Optional[str] = None
    offer_deadline: Optional[datetime] = None
    lessons_learned: Optional[str] = None
    response_time_days: Optional[float] = None


class OutcomeUpdate(BaseModel):
    """Payload to update an existing outcome record."""
    final_status: Optional[ApplicationStatus] = None
    rejection_category: Optional[RejectionCategory] = None
    rejection_feedback: Optional[str] = None
    offer_outcome: Optional[OfferOutcome] = None
    offer_salary_amount: Optional[float] = None
    offer_salary_currency: Optional[str] = None
    offer_equity: Optional[str] = None
    offer_bonus: Optional[str] = None
    offer_deadline: Optional[datetime] = None
    lessons_learned: Optional[str] = None
    response_time_days: Optional[float] = None


class OutcomeRead(BaseModel):
    """Representation of an application terminal outcome."""
    id: uuid.UUID
    application_id: uuid.UUID
    final_status: ApplicationStatus
    rejection_category: Optional[RejectionCategory] = None
    rejection_feedback: Optional[str] = None
    offer_outcome: Optional[OfferOutcome] = None
    offer_salary_amount: Optional[float] = None
    offer_salary_currency: Optional[str] = None
    offer_equity: Optional[str] = None
    offer_bonus: Optional[str] = None
    offer_deadline: Optional[datetime] = None
    lessons_learned: Optional[str] = None
    response_time_days: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# KanBan Board Schemas
# ---------------------------------------------------------------------------

class KanbanCardRead(BaseModel):
    """A card on the application lifecycle KanBan board."""
    application_id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    platform: Optional[str] = None
    status: ApplicationStatus
    match_score: Optional[float] = None
    days_in_stage: int = 0
    interview_count: int = 0
    next_interview_at: Optional[datetime] = None
    timeline_event_count: int = 0
    applied_at: Optional[datetime] = None
    updated_at: datetime


class KanbanColumn(BaseModel):
    """A single status column in the KanBan board."""
    status: ApplicationStatus
    label: str
    total_count: int
    applications: List[KanbanCardRead] = Field(default_factory=list)


class KanbanBoardRead(BaseModel):
    """Full KanBan board view partitioned by application lifecycle status."""
    candidate_id: uuid.UUID
    total_active_applications: int
    total_completed_applications: int
    columns: List[KanbanColumn]


# ---------------------------------------------------------------------------
# Analytics Schemas (TRK-003)
# ---------------------------------------------------------------------------

class FunnelStageMetric(BaseModel):
    """Conversion statistics for an application funnel stage."""
    stage: ApplicationStatus
    count: int
    conversion_from_applied_pct: float
    dropoff_count: int


class FunnelAnalyticsRead(BaseModel):
    """Full conversion funnel from Discovered to Accepted."""
    total_discovered: int
    total_saved: int
    total_applied: int
    total_screening: int
    total_interviewing: int
    total_offers: int
    total_accepted: int
    total_rejected: int
    total_withdrawn: int
    applied_to_interview_rate_pct: float
    applied_to_offer_rate_pct: float
    stages: List[FunnelStageMetric]


class SkillGapTrend(BaseModel):
    """Analytics on skills commonly missing in rejected vs applied jobs."""
    skill_name: str
    missing_in_rejected_count: int
    missing_in_applied_count: int
    impact_frequency_pct: float
    priority_level: str  # HIGH, MEDIUM, LOW


class SkillGapAnalyticsRead(BaseModel):
    """Skill gap analysis across tracked applications."""
    candidate_id: uuid.UUID
    total_rejections_analyzed: int
    total_applications_analyzed: int
    top_skill_gaps: List[SkillGapTrend]


class ResponseTimeAnalyticsRead(BaseModel):
    """Response duration and velocity metrics across applications."""
    avg_days_to_first_response: Optional[float] = None
    avg_days_to_interview: Optional[float] = None
    avg_days_to_offer: Optional[float] = None
    avg_days_to_rejection: Optional[float] = None
    ghost_rate_pct: float = 0.0


class MatchScoreOutcomeCorrelation(BaseModel):
    """Statistical correlation between algorithmic match score and real-world outcome."""
    avg_match_score_all: float
    avg_match_score_interviewed: Optional[float] = None
    avg_match_score_offered: Optional[float] = None
    avg_match_score_rejected: Optional[float] = None
    correlation_insight: str


class TrackingDashboardSummary(BaseModel):
    """Aggregate tracking dashboard overview."""
    candidate_id: uuid.UUID
    active_applications_count: int
    upcoming_interviews_count: int
    offers_count: int
    rejections_count: int
    funnel: FunnelAnalyticsRead
    response_times: ResponseTimeAnalyticsRead
    top_skill_gaps: List[SkillGapTrend]
    match_score_correlation: MatchScoreOutcomeCorrelation
