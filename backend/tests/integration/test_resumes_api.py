"""Integration tests for Resume Tailoring & Intelligence REST API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tailored_and_master_resume_pipeline(async_client: AsyncClient):
    """End-to-end integration test: Profile -> Verified Facts -> Tailored Resume -> Master Resume -> Update."""

    # 1. Create Candidate Profile
    cand_payload = {
        "full_name": "Jordan Resume",
        "email": "jordan.resume@example.com",
        "current_title": "Senior AI & Cloud Engineer",
        "target_roles": ["Senior AI Engineer", "Backend Architect"],
        "location": "Remote",
        "work_mode": "REMOTE"
    }
    cand_res = await async_client.post("/api/v1/candidate", json=cand_payload)
    assert cand_res.status_code == 201
    candidate_id = cand_res.json()["id"]

    # 2. Add Verified Skills
    skills = ["Python", "FastAPI", "pgvector", "Docker"]
    for s in skills:
        sk_res = await async_client.post(
            "/api/v1/candidate/skills",
            json={"skill_name": s, "state": "VERIFIED", "years_experience": 4.5}
        )
        assert sk_res.status_code == 201

    # 3. Add Experience
    exp_payload = {
        "company": "NeuralScale",
        "title": "Senior AI Infrastructure Engineer",
        "start_date": "2021-01-01",
        "end_date": "2024-01-01",
        "is_current": False
    }
    exp_res = await async_client.post("/api/v1/candidate/experiences", json=exp_payload)
    assert exp_res.status_code == 201

    # 4. Add Verified Achievement Fact
    fact_payload = {
        "fact_type": "ACHIEVEMENT",
        "title": "LLM Semantic Cache Acceleration",
        "description": "Reduced inference cost by 35% with Redis and pgvector semantic caching.",
        "metrics": {"cost_reduction_pct": 35},
        "source_reference": "NeuralScale Q2 Review",
        "verification_status": "VERIFIED",
        "tags": ["pgvector", "redis", "optimization"]
    }
    fact_res = await async_client.post("/api/v1/candidate/facts", json=fact_payload)
    assert fact_res.status_code == 201

    # 5. Ingest Target Job
    job_payload = {
        "title": "Lead AI Systems Engineer",
        "company": "ScaleAI Labs",
        "description": "Requires Python, FastAPI, and pgvector. Must have experience optimizing retrieval pipelines.",
        "location": "Remote",
        "work_mode": "REMOTE",
        "min_experience_years": 4.0,
        "required_skills": ["Python", "FastAPI", "pgvector"],
        "preferred_skills": ["Docker"],
        "source": "DIRECT",
        "application_url": "https://scaleai.example.com/apply/001"
    }
    job_res = await async_client.post("/api/v1/jobs/ingest", json=job_payload)
    assert job_res.status_code == 201
    job_id = job_res.json()["job"]["id"]

    # 6. Generate Tailored Resume
    tailor_payload = {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "include_claimed_skills": False,
        "max_bullets_per_experience": 3
    }
    tailor_res = await async_client.post("/api/v1/resumes/tailor", json=tailor_payload)
    assert tailor_res.status_code == 201
    tailor_data = tailor_res.json()

    resume_id = tailor_data["id"]
    assert tailor_data["candidate_id"] == candidate_id
    assert tailor_data["job_id"] == job_id
    assert tailor_data["truth_score"] == 100.0
    assert "pgvector" in tailor_data["targeted_skills"]
    assert "LLM Semantic Cache Acceleration" in tailor_data["raw_markdown"]

    # 7. Get Resume by ID
    get_res = await async_client.get(f"/api/v1/resumes/{resume_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == resume_id

    # 8. Update Resume Status (User approval)
    update_res = await async_client.put(
        f"/api/v1/resumes/{resume_id}",
        json={"status": "APPROVED", "user_notes": "Reviewed and ready for submission"}
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "APPROVED"
    assert update_res.json()["user_notes"] == "Reviewed and ready for submission"

    # 9. Generate Master Resume
    master_res = await async_client.post(
        "/api/v1/resumes/master",
        json={"candidate_id": candidate_id, "title": "Comprehensive Master Technical Resume"}
    )
    assert master_res.status_code == 201
    master_data = master_res.json()
    assert master_data["is_master"] is True
    assert master_data["truth_score"] == 100.0

    # 10. List All Resumes for Candidate
    list_res = await async_client.get(f"/api/v1/resumes?candidate_id={candidate_id}")
    assert list_res.status_code == 200
    resumes_list = list_res.json()
    assert len(resumes_list) >= 2
