"""Integration tests for Matching Engine REST API routes."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_single_and_batch_matching_workflow(async_client: AsyncClient):
    """End-to-end integration test: Profile -> Jobs -> Single Match -> Batch Match -> Top Matches."""
    
    # 1. Create Candidate Profile
    cand_payload = {
        "full_name": "Dev Matcher",
        "email": "matcher@example.com",
        "current_title": "Senior Backend Engineer",
        "target_roles": ["Senior Backend Engineer", "Lead Python Engineer"],
        "location": "Remote",
        "work_mode": "REMOTE"
    }
    cand_res = await async_client.post("/api/v1/candidate", json=cand_payload)
    assert cand_res.status_code == 201
    candidate_id = cand_res.json()["id"]

    # 2. Add Verified Skills
    skills_to_add = ["Python", "FastAPI", "PostgreSQL"]
    for sk in skills_to_add:
        sk_res = await async_client.post(
            "/api/v1/candidate/skills",
            json={"skill_name": sk, "state": "VERIFIED", "years_experience": 4.0}
        )
        assert sk_res.status_code == 201

    # 3. Add Experience Record (4 years)
    exp_payload = {
        "company": "CloudForge",
        "title": "Backend Engineer",
        "start_date": "2020-01-01",
        "end_date": "2024-01-01",
        "is_current": False
    }
    exp_res = await async_client.post("/api/v1/candidate/experiences", json=exp_payload)
    assert exp_res.status_code == 201

    # 4. Ingest Job 1: Strong Match (Remote, Python, FastAPI, 3-5 yrs)
    job1_payload = {
        "title": "Senior Python Developer",
        "company": "NexusAI",
        "description": "Looking for a Senior Python Developer with FastAPI and PostgreSQL expertise. 4+ years experience. Fully remote.",
        "location": "Remote",
        "work_mode": "REMOTE",
        "min_experience_years": 4.0,
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "source": "DIRECT",
        "application_url": "https://nexusai.com/jobs/1"
    }
    job1_res = await async_client.post("/api/v1/jobs/ingest", json=job1_payload)
    assert job1_res.status_code == 201
    job1_id = job1_res.json()["job"]["id"]

    # 5. Ingest Job 2: Mismatch Job (Onsite, Java/Kotlin, 10+ yrs)
    job2_payload = {
        "title": "Director of Java Architecture",
        "company": "LegacyCorp",
        "description": "Requires 10+ years of Java, Spring Boot, and Onsite presence in Tokyo.",
        "location": "Tokyo",
        "work_mode": "ONSITE",
        "min_experience_years": 10.0,
        "required_skills": ["Java", "Spring Boot"],
        "source": "DIRECT",
        "application_url": "https://legacycorp.com/jobs/2"
    }
    job2_res = await async_client.post("/api/v1/jobs/ingest", json=job2_payload)
    assert job2_res.status_code == 201
    job2_id = job2_res.json()["job"]["id"]

    # 6. Evaluate Job 1 (Single Evaluation)
    eval_res = await async_client.post(
        "/api/v1/matching/evaluate",
        json={"candidate_id": candidate_id, "job_id": job1_id}
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["status"] in ["STRONG_MATCH", "MODERATE_MATCH"]
    assert eval_data["breakdown"]["passed_hard_filters"] is True
    assert eval_data["breakdown"]["overall_score"] >= 80.0
    assert "Python" in eval_data["breakdown"]["matched_skills"]
    assert len(eval_data["breakdown"]["highlights"]) >= 1

    # 7. Evaluate Job 2 (Should fail hard filters)
    eval2_res = await async_client.post(
        "/api/v1/matching/evaluate",
        json={"candidate_id": candidate_id, "job_id": job2_id}
    )
    assert eval2_res.status_code == 200
    eval2_data = eval2_res.json()
    assert eval2_data["status"] == "FILTERED_OUT"
    assert eval2_data["breakdown"]["passed_hard_filters"] is False
    assert len(eval2_data["breakdown"]["rejection_reasons"]) >= 1

    # 8. Batch Match Execution
    batch_res = await async_client.post(
        "/api/v1/matching/batch",
        json={"candidate_id": candidate_id, "min_score": 50.0, "only_passed_filters": True}
    )
    assert batch_res.status_code == 200
    batch_data = batch_res.json()
    assert batch_data["total_jobs_evaluated"] >= 2
    assert batch_data["qualified_matches_count"] >= 1
    top_match = batch_data["matches"][0]
    assert top_match["job_id"] == job1_id
    assert top_match["overall_score"] >= 80.0

    # 9. Query Top Matches Endpoint
    top_res = await async_client.get(f"/api/v1/matching/top-matches?candidate_id={candidate_id}")
    assert top_res.status_code == 200
    top_list = top_res.json()
    assert len(top_list) >= 1
    assert top_list[0]["job_id"] == job1_id
