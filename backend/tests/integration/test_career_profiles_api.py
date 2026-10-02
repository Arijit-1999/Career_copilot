"""Integration tests for Career Search Profiles and Intent Expansion REST API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_career_intent_expansion_endpoint(async_client: AsyncClient):
    """Test POST /api/v1/career-profiles/expand-intent expands natural-language intent."""
    payload = {
        "query": "I want a Python backend role with AWS cloud deployment and microservices"
    }
    response = await async_client.post("/api/v1/career-profiles/expand-intent", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "Python Backend Engineer" in data["primary_roles"]
    assert len(data["alternative_roles"]) > 0
    assert "Python" in data["recommended_skills"]
    assert data["expansion_method"] == "deterministic_ontology"


@pytest.mark.asyncio
async def test_search_profile_crud_flow(async_client: AsyncClient):
    """Test full CRUD lifecycle for CareerSearchProfile."""
    # Ensure active candidate exists
    await async_client.get("/api/v1/candidate/me")

    # 1. Create Search Profile
    create_payload = {
        "name": "Backend Python Track",
        "target_roles": ["Python Backend Engineer", "Cloud Application Engineer"],
        "alternative_roles": ["Python Application Developer"],
        "required_skills": ["Python", "FastAPI", "SQL"],
        "preferred_skills": ["Docker", "PostgreSQL"],
        "excluded_skills": ["Java", "C#"],
        "locations": ["Bengaluru", "Remote"],
        "work_modes": ["REMOTE", "HYBRID"],
        "min_experience_years": 2.5,
        "max_experience_years": 6.0,
        "min_salary": 1800000.0,
        "target_salary": 2500000.0,
        "currency": "INR",
        "is_active": True,
        "intent_query": "Python and cloud backend development"
    }
    create_res = await async_client.post("/api/v1/career-profiles", json=create_payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    profile_id = created_data["id"]
    assert created_data["name"] == "Backend Python Track"
    assert created_data["min_experience_years"] == 2.5

    # 2. List Profiles
    list_res = await async_client.get("/api/v1/career-profiles")
    assert list_res.status_code == 200
    profiles = list_res.json()
    assert len(profiles) >= 1
    assert any(p["id"] == profile_id for p in profiles)

    # 3. Get Specific Profile
    get_res = await async_client.get(f"/api/v1/career-profiles/{profile_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Backend Python Track"

    # 4. Update Profile
    update_payload = {
        "target_salary": 2800000.0,
        "is_active": True
    }
    update_res = await async_client.put(f"/api/v1/career-profiles/{profile_id}", json=update_payload)
    assert update_res.status_code == 200
    assert update_res.json()["target_salary"] == 2800000.0

    # 5. Delete Profile
    del_res = await async_client.delete(f"/api/v1/career-profiles/{profile_id}")
    assert del_res.status_code == 204

    # 6. Verify Deletion
    verify_res = await async_client.get(f"/api/v1/career-profiles/{profile_id}")
    assert verify_res.status_code == 404
