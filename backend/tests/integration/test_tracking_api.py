"""Integration tests for Tracking & Analytics REST API."""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_add_and_get_timeline_events(async_client: AsyncClient) -> None:
    # 1. Create candidate
    cand_res = await async_client.post(
        "/api/v1/candidate",
        json={"full_name": "Alice Tracking", "email": f"alice.{uuid.uuid4().hex[:6]}@example.com"},
    )
    assert cand_res.status_code == 201
    candidate_id = cand_res.json()["id"]

    # 2. Create application
    app_res = await async_client.post(
        "/api/v1/applications",
        json={"candidate_id": candidate_id, "platform": "linkedin"},
    )
    assert app_res.status_code == 201
    app_id = app_res.json()["id"]

    # 3. Add timeline event
    res = await async_client.post(
        f"/api/v1/tracking/applications/{app_id}/timeline",
        json={
            "event_type": "NOTE_ADDED",
            "title": "Recruiter message",
            "description": "Recruiter replied on LinkedIn offering initial screen.",
            "extra_data": {"channel": "linkedin_inmail"},
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Recruiter message"
    assert data["application_id"] == app_id

    # 4. Get timeline history
    get_res = await async_client.get(f"/api/v1/tracking/applications/{app_id}/timeline")
    assert get_res.status_code == 200
    events = get_res.json()
    assert len(events) >= 1
    assert events[0]["title"] == "Recruiter message"


@pytest.mark.asyncio
async def test_interview_lifecycle_api(async_client: AsyncClient) -> None:
    # 1. Create candidate & application
    cand_res = await async_client.post(
        "/api/v1/candidate",
        json={"full_name": "Bob Tracking", "email": f"bob.{uuid.uuid4().hex[:6]}@example.com"},
    )
    candidate_id = cand_res.json()["id"]
    app_res = await async_client.post(
        "/api/v1/applications",
        json={"candidate_id": candidate_id, "platform": "naukri"},
    )
    app_id = app_res.json()["id"]

    # 2. Schedule Interview
    res = await async_client.post(
        f"/api/v1/tracking/applications/{app_id}/interviews",
        json={
            "round_type": "TECHNICAL_ASSESSMENT",
            "round_number": 1,
            "format": "ASYNC_ASSESSMENT",
            "duration_minutes": 90,
            "preparation_notes": "Review async Python concurrency and SQL optimization.",
        },
    )
    assert res.status_code == 201
    interview = res.json()
    interview_id = interview["id"]
    assert interview["round_type"] == "TECHNICAL_ASSESSMENT"
    assert interview["outcome"] == "SCHEDULED"

    # 3. List interviews
    list_res = await async_client.get(f"/api/v1/tracking/applications/{app_id}/interviews")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 4. Patch interview outcome
    patch_res = await async_client.patch(
        f"/api/v1/tracking/interviews/{interview_id}",
        json={
            "outcome": "PASSED",
            "feedback_received": "Scored 95% on backend problem set.",
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["outcome"] == "PASSED"


@pytest.mark.asyncio
async def test_record_outcome_api(async_client: AsyncClient) -> None:
    # 1. Create candidate & application
    cand_res = await async_client.post(
        "/api/v1/candidate",
        json={"full_name": "Carol Tracking", "email": f"carol.{uuid.uuid4().hex[:6]}@example.com"},
    )
    candidate_id = cand_res.json()["id"]
    app_res = await async_client.post(
        "/api/v1/applications",
        json={"candidate_id": candidate_id, "platform": "indeed"},
    )
    app_id = app_res.json()["id"]

    # 2. Record offer
    res = await async_client.post(
        f"/api/v1/tracking/applications/{app_id}/outcome",
        json={
            "final_status": "OFFER",
            "offer_outcome": "PENDING_DECISION",
            "offer_salary_amount": 3200000.0,
            "offer_salary_currency": "INR",
            "offer_equity": "10,000 RSUs",
            "lessons_learned": "Great team alignment.",
        },
    )
    assert res.status_code == 200
    outcome = res.json()
    assert outcome["final_status"] == "OFFER"
    assert outcome["offer_salary_amount"] == 3200000.0

    # 3. Fetch outcome
    get_res = await async_client.get(f"/api/v1/tracking/applications/{app_id}/outcome")
    assert get_res.status_code == 200
    assert get_res.json()["final_status"] == "OFFER"


@pytest.mark.asyncio
async def test_kanban_and_analytics_endpoints(async_client: AsyncClient) -> None:
    # 1. Create candidate & application
    cand_res = await async_client.post(
        "/api/v1/candidate",
        json={"full_name": "Dave Tracking", "email": f"dave.{uuid.uuid4().hex[:6]}@example.com"},
    )
    candidate_id = cand_res.json()["id"]
    await async_client.post(
        "/api/v1/applications",
        json={"candidate_id": candidate_id, "platform": "linkedin"},
    )

    # 2. KanBan board
    kb_res = await async_client.get(f"/api/v1/tracking/candidates/{candidate_id}/kanban")
    assert kb_res.status_code == 200
    kb_data = kb_res.json()
    assert kb_data["candidate_id"] == candidate_id
    assert "columns" in kb_data
    assert len(kb_data["columns"]) == 10

    # 3. Funnel Analytics
    funnel_res = await async_client.get(f"/api/v1/tracking/candidates/{candidate_id}/analytics/funnel")
    assert funnel_res.status_code == 200
    assert "stages" in funnel_res.json()

    # 4. Skill Gaps Analytics
    gaps_res = await async_client.get(f"/api/v1/tracking/candidates/{candidate_id}/analytics/skill-gaps")
    assert gaps_res.status_code == 200
    assert "top_skill_gaps" in gaps_res.json()

    # 5. Response Time Analytics
    rt_res = await async_client.get(f"/api/v1/tracking/candidates/{candidate_id}/analytics/response-times")
    assert rt_res.status_code == 200
    assert "ghost_rate_pct" in rt_res.json()

    # 6. Match Correlation Analytics
    mc_res = await async_client.get(f"/api/v1/tracking/candidates/{candidate_id}/analytics/match-correlation")
    assert mc_res.status_code == 200
    assert "avg_match_score_all" in mc_res.json()

    # 7. Full Dashboard Summary
    dash_res = await async_client.get(f"/api/v1/tracking/candidates/{candidate_id}/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["candidate_id"] == candidate_id
    assert "funnel" in dash_data
    assert "top_skill_gaps" in dash_data
