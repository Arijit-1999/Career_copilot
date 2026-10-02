"""Integration tests for Job Understanding and Extraction API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stateless_jd_analysis_endpoint(async_client: AsyncClient):
    """Test POST /api/v1/extraction/analyze without needing a stored job."""
    payload = {
        "title": "Lead Python & Data Platform Engineer",
        "company": "DeepScale Labs",
        "description": """
        About the Role:
        Lead our data platform and AI microservices team.

        Requirements:
        - 6+ years of software engineering experience.
        - Expert Python, FastAPI, and PostgreSQL skills.
        - Experience with Redis, Docker, and Kubernetes.

        Good to Have:
        - Prior work with pgvector, Snowflake, and AWS.
        """
    }

    res = await async_client.post("/api/v1/extraction/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["title"] == payload["title"]
    assert data["company"] == payload["company"]
    result = data["result"]
    assert result["seniority"] == "LEAD"
    assert result["min_experience_years"] == 6.0
    assert "Python" in result["required_skills"]
    assert "FastAPI" in result["required_skills"]
    assert "PostgreSQL" in result["required_skills"]
    assert "AWS" in result["preferred_skills"]
    assert "pgvector" in result["preferred_skills"] or "Snowflake" in result["preferred_skills"]


@pytest.mark.asyncio
async def test_extract_and_persist_to_job(async_client: AsyncClient):
    """Test POST /api/v1/extraction/jobs/{job_id}/extract to enrich an existing job."""
    # 1. Ingest a new raw job
    ingest_payload = {
        "title": "Senior Backend Developer",
        "company": "DataMatrix AI",
        "description": """
        Requirements:
        - Strong Python, Django, and PostgreSQL experience.
        - 5+ years of experience.
        
        Preferred:
        - Experience with Docker and AWS.
        """,
        "source": "DIRECT",
        "application_url": "https://datamatrix.ai/careers/001"
    }

    ingest_res = await async_client.post("/api/v1/jobs/ingest", json=ingest_payload)
    assert ingest_res.status_code == 201
    job_id = ingest_res.json()["job"]["id"]

    # 2. Trigger Extraction & Enrichment
    extract_res = await async_client.post(f"/api/v1/extraction/jobs/{job_id}/extract")
    assert extract_res.status_code == 200
    extract_data = extract_res.json()
    assert extract_data["job_id"] == job_id
    res_obj = extract_data["result"]
    assert "Django" in res_obj["required_skills"]
    assert "PostgreSQL" in res_obj["required_skills"]

    # 3. Retrieve Job and Verify Enriched Fields
    job_get_res = await async_client.get(f"/api/v1/jobs/{job_id}")
    assert job_get_res.status_code == 200
    saved_job = job_get_res.json()
    assert "Django" in saved_job["required_skills"]
    assert "PostgreSQL" in saved_job["required_skills"]
    assert saved_job["min_experience_years"] == 5.0
