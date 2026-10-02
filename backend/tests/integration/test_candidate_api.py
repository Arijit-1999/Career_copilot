"""Integration tests for Candidate domain REST API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_candidate_profile(async_client: AsyncClient):
    """Test creating candidate profile and retrieving it via /me."""
    payload = {
        "full_name": "Arijit Developer",
        "email": "arijit.dev@example.com",
        "phone": "+91-9876543210",
        "location": "Bengaluru, India",
        "current_title": "Senior Python Engineer",
        "summary": "Full-stack Python and Cloud Engineer with 5+ years building backend systems.",
        "target_roles": ["Python Backend Engineer", "AWS Data Engineer"],
        "work_mode": "HYBRID",
        "min_salary": 2000000.0,
        "target_salary": 2800000.0,
        "currency": "INR"
    }

    # 1. Create Profile
    res = await async_client.post("/api/v1/candidate", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["full_name"] == "Arijit Developer"
    assert data["email"] == "arijit.dev@example.com"
    assert data["work_mode"] == "HYBRID"
    assert len(data["target_roles"]) == 2

    # 2. Retrieve Profile via /me
    me_res = await async_client.get("/api/v1/candidate/me")
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "arijit.dev@example.com"


@pytest.mark.asyncio
async def test_add_and_filter_candidate_skills(async_client: AsyncClient):
    """Test adding skills with different states and filtering by VERIFIED status."""
    # Ensure active profile exists
    await async_client.get("/api/v1/candidate/me")

    # Add CLAIMED skill
    skill_1 = {
        "skill_name": "Kubernetes",
        "category": "DevOps",
        "state": "CLAIMED",
        "confidence_level": 3
    }
    res_1 = await async_client.post("/api/v1/candidate/skills", json=skill_1)
    assert res_1.status_code == 201
    assert res_1.json()["state"] == "CLAIMED"

    # Add VERIFIED skill
    skill_2 = {
        "skill_name": "Python",
        "category": "Languages",
        "state": "VERIFIED",
        "years_experience": 5.5,
        "confidence_level": 5,
        "evidence_notes": "Built production microservices and data pipelines"
    }
    res_2 = await async_client.post("/api/v1/candidate/skills", json=skill_2)
    assert res_2.status_code == 201
    data_2 = res_2.json()
    assert data_2["state"] == "VERIFIED"
    assert data_2["verified_at"] is not None

    # Filter all skills
    all_res = await async_client.get("/api/v1/candidate/skills")
    assert all_res.status_code == 200
    assert len(all_res.json()) == 2

    # Filter ONLY VERIFIED skills
    verified_res = await async_client.get("/api/v1/candidate/skills?state=VERIFIED")
    assert verified_res.status_code == 200
    verified_skills = verified_res.json()
    assert len(verified_skills) == 1
    assert verified_skills[0]["skill_name"] == "Python"
    assert verified_skills[0]["state"] == "VERIFIED"


@pytest.mark.asyncio
async def test_add_and_query_resume_facts(async_client: AsyncClient):
    """Test adding structured facts to Resume Fact Bank and querying with verification filter."""
    await async_client.get("/api/v1/candidate/me")

    fact_payload = {
        "fact_type": "ACHIEVEMENT",
        "title": "Database Query Optimization",
        "description": "Reduced API response times by 40% through indexing and async query batching",
        "metrics": {"latency_reduction_pct": 40},
        "source_reference": "Performance Review Q3 2024",
        "verification_status": "VERIFIED",
        "tags": ["postgresql", "optimization"]
    }

    create_res = await async_client.post("/api/v1/candidate/facts", json=fact_payload)
    assert create_res.status_code == 201
    fact_data = create_res.json()
    assert fact_data["title"] == "Database Query Optimization"
    assert fact_data["verification_status"] == "VERIFIED"

    # Query verified facts
    query_res = await async_client.get("/api/v1/candidate/facts?verification_status=VERIFIED")
    assert query_res.status_code == 200
    facts = query_res.json()
    assert len(facts) >= 1
    assert facts[0]["verification_status"] == "VERIFIED"


@pytest.mark.asyncio
async def test_add_experience_and_projects(async_client: AsyncClient):
    """Test adding employment experience and portfolio project records."""
    await async_client.get("/api/v1/candidate/me")

    # Add experience
    exp_payload = {
        "company": "Tech Solutions Corp",
        "title": "Senior Software Engineer",
        "location": "Bengaluru",
        "start_date": "2022-01-01",
        "is_current": True,
        "description": "Leading cloud backend development."
    }
    exp_res = await async_client.post("/api/v1/candidate/experiences", json=exp_payload)
    assert exp_res.status_code == 201
    assert exp_res.json()["company"] == "Tech Solutions Corp"

    # Add project
    proj_payload = {
        "name": "Data Pipeline Orchestrator",
        "role": "Lead Architect",
        "description": "High-throughput data streaming pipeline.",
        "tech_stack": ["Python", "FastAPI", "PostgreSQL", "pgvector"],
        "url": "https://example.com/project"
    }
    proj_res = await async_client.post("/api/v1/candidate/projects", json=proj_payload)
    assert proj_res.status_code == 201
    assert proj_res.json()["name"] == "Data Pipeline Orchestrator"
