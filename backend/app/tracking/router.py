"""FastAPI router for Application Tracking, KanBan, and Analytics domain."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.tracking.service import TrackingService
from app.tracking.schemas import (
    TimelineEventCreate,
    TimelineEventRead,
    InterviewCreate,
    InterviewUpdate,
    InterviewRead,
    OutcomeCreate,
    OutcomeRead,
    KanbanBoardRead,
    FunnelAnalyticsRead,
    SkillGapAnalyticsRead,
    ResponseTimeAnalyticsRead,
    MatchScoreOutcomeCorrelation,
    TrackingDashboardSummary,
)

router = APIRouter(prefix="/tracking", tags=["Tracking & Analytics"])
tracking_service = TrackingService()


# ---------------------------------------------------------------------------
# Timeline Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/applications/{application_id}/timeline",
    response_model=TimelineEventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add timeline event",
    description="Logs a new milestone, state transition, or event to an application's history.",
)
async def add_timeline_event(
    application_id: uuid.UUID,
    payload: TimelineEventCreate,
    db: AsyncSession = Depends(get_db_session),
) -> TimelineEventRead:
    return await tracking_service.add_timeline_event(db, application_id, payload)


@router.get(
    "/applications/{application_id}/timeline",
    response_model=List[TimelineEventRead],
    summary="Get application timeline",
    description="Retrieves the full chronological milestone history for an application.",
)
async def get_application_timeline(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> List[TimelineEventRead]:
    return await tracking_service.get_application_timeline(db, application_id)


# ---------------------------------------------------------------------------
# Interview Tracking Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/applications/{application_id}/interviews",
    response_model=InterviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule / log interview",
    description="Schedules or logs an interview round and automatically updates timeline events.",
)
async def schedule_interview(
    application_id: uuid.UUID,
    payload: InterviewCreate,
    db: AsyncSession = Depends(get_db_session),
) -> InterviewRead:
    return await tracking_service.create_interview(db, application_id, payload)


@router.get(
    "/applications/{application_id}/interviews",
    response_model=List[InterviewRead],
    summary="Get application interviews",
    description="Lists all interview rounds recorded for an application.",
)
async def get_application_interviews(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> List[InterviewRead]:
    return await tracking_service.get_application_interviews(db, application_id)


@router.patch(
    "/interviews/{interview_id}",
    response_model=InterviewRead,
    summary="Update interview notes / outcome",
    description="Updates interview preparation notes, interviewer debrief, questions, or outcome status.",
)
async def update_interview(
    interview_id: uuid.UUID,
    payload: InterviewUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> InterviewRead:
    return await tracking_service.update_interview(db, interview_id, payload)


# ---------------------------------------------------------------------------
# Terminal Outcome Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/applications/{application_id}/outcome",
    response_model=OutcomeRead,
    status_code=status.HTTP_200_OK,
    summary="Record terminal outcome",
    description="Records terminal resolution (offer, rejection, acceptance) with compensation or rejection taxonomy.",
)
async def record_application_outcome(
    application_id: uuid.UUID,
    payload: OutcomeCreate,
    db: AsyncSession = Depends(get_db_session),
) -> OutcomeRead:
    return await tracking_service.record_outcome(db, application_id, payload)


@router.get(
    "/applications/{application_id}/outcome",
    response_model=Optional[OutcomeRead],
    summary="Get application outcome",
    description="Fetches recorded outcome details for an application.",
)
async def get_application_outcome(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> Optional[OutcomeRead]:
    return await tracking_service.get_outcome(db, application_id)


# ---------------------------------------------------------------------------
# KanBan Board & Analytics Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/candidates/{candidate_id}/kanban",
    response_model=KanbanBoardRead,
    summary="Get KanBan board",
    description="Fetches an aggregate KanBan board view with applications partitioned across stages.",
)
async def get_kanban_board(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> KanbanBoardRead:
    return await tracking_service.get_kanban_board(db, candidate_id)


@router.get(
    "/candidates/{candidate_id}/analytics/funnel",
    response_model=FunnelAnalyticsRead,
    summary="Get conversion funnel analytics",
    description="Computes conversion rates from Applied to Screening, Interviewing, and Offers.",
)
async def get_funnel_analytics(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> FunnelAnalyticsRead:
    return await tracking_service.get_funnel_analytics(db, candidate_id)


@router.get(
    "/candidates/{candidate_id}/analytics/skill-gaps",
    response_model=SkillGapAnalyticsRead,
    summary="Get skill gap analytics",
    description="Identifies top missing skills and frequencies in rejected vs applied jobs.",
)
async def get_skill_gap_analytics(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> SkillGapAnalyticsRead:
    return await tracking_service.get_skill_gap_analytics(db, candidate_id)


@router.get(
    "/candidates/{candidate_id}/analytics/response-times",
    response_model=ResponseTimeAnalyticsRead,
    summary="Get response time velocity",
    description="Calculates average response velocities and ghosting rate across applications.",
)
async def get_response_time_analytics(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ResponseTimeAnalyticsRead:
    return await tracking_service.get_response_time_analytics(db, candidate_id)


@router.get(
    "/candidates/{candidate_id}/analytics/match-correlation",
    response_model=MatchScoreOutcomeCorrelation,
    summary="Get match score vs outcome correlation",
    description="Analyzes statistical correlation between AI match scores and interview conversion.",
)
async def get_match_score_correlation(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> MatchScoreOutcomeCorrelation:
    return await tracking_service.get_match_score_correlation(db, candidate_id)


@router.get(
    "/candidates/{candidate_id}/dashboard",
    response_model=TrackingDashboardSummary,
    summary="Get full tracking dashboard summary",
    description="Aggregates active metrics, upcoming interviews, funnel, response times, and skill gaps.",
)
async def get_dashboard_summary(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> TrackingDashboardSummary:
    return await tracking_service.get_dashboard_summary(db, candidate_id)
