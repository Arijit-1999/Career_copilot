"""Integration tests for Job Ingestion, Deduplication, and Search REST API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ingest_single_job_and_deduplication(async_client: AsyncClient):
    """Test single job ingestion and multi-signal deduplication handling."""
    job_payload = {
        "title": "[Urgent] Senior Python Backend Developer (Remote)",
        "company": "ScaleTech Systems",
        "description": "<p>We are looking for a <strong>Senior Python Developer</strong> with FastAPI and PostgreSQL experience.</p>",
        "source": "LINKEDIN",
        "source_job_id": "linkedin_job_998811",
        "application_url": "https://www.linkedin.com/jobs/view/998811/?utm_source=feed&refId=xyz",
        "location": "Bengaluru (Remote)",
        "salary_raw": "₹22L - ₹32L",
        "min_experience_years": 4.0,
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"]
    }

    # 1. Ingest New Job
    res = await async_client.post("/api/v1/jobs/ingest", json=job_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["is_duplicate"] is False
    assert data["action"] == "created"
    job = data["job"]
    job_id = job["id"]
    assert job["normalized_title"] == "Senior Python Backend Developer"
    assert job["salary_min"] == 2200000.0
    assert job["salary_max"] == 3200000.0
    assert job["work_mode"] == "REMOTE"
    assert job["canonical_url"] == "https://www.linkedin.com/jobs/view/998811"
    assert "<p>" not in job["description_clean"]

    # 2. Ingest the Exact Same Job Again (Deduplication Check)
    dup_res = await async_client.post("/api/v1/jobs/ingest", json=job_payload)
    assert dup_res.status_code == 201
    dup_data = dup_res.json()
    assert dup_data["is_duplicate"] is True
    assert dup_data["action"] == "seen_again"
    assert dup_data["job"]["id"] == job_id


@pytest.mark.asyncio
async def test_batch_ingest_and_filter_jobs(async_client: AsyncClient):
    """Test batch job ingestion and filtered search queries."""
    batch_payload = {
        "jobs": [
            {
                "title": "AWS Data Engineer",
                "company": "CloudData Analytics",
                "description": "Building data pipelines with PySpark, AWS S3, and Glue.",
                "source": "NAUKRI",
                "source_job_id": "naukri_data_001",
                "location": "Hyderabad",
                "work_mode": "HYBRID",
                "salary_raw": "20 - 30 LPA",
                "required_skills": ["Python", "AWS", "PySpark", "SQL"]
            },
            {
                "title": "Full Stack Engineer",
                "company": "WebTech Labs",
                "description": "Building modern web apps with Python and React.",
                "source": "INDEED",
                "source_job_id": "indeed_fs_002",
                "location": "Mumbai",
                "work_mode": "ONSITE",
                "salary_raw": "15 - 20 LPA",
                "required_skills": ["Python", "React", "JavaScript"]
            }
        ]
    }

    # 1. Batch Ingest
    batch_res = await async_client.post("/api/v1/jobs/batch-ingest", json=batch_payload)
    assert batch_res.status_code == 201
    batch_data = batch_res.json()
    assert batch_data["total_received"] == 2
    assert batch_data["new_jobs_added"] == 2
    assert batch_data["duplicates_seen"] == 0

    # 2. Search by Keyword "PySpark"
    pyspark_res = await async_client.get("/api/v1/jobs?keyword=PySpark")
    assert pyspark_res.status_code == 200
    pyspark_jobs = pyspark_res.json()
    assert len(pyspark_jobs) >= 1
    assert "PySpark" in pyspark_jobs[0]["description_clean"]

    # 3. Filter by Work Mode "HYBRID"
    hybrid_res = await async_client.get("/api/v1/jobs?work_mode=HYBRID")
    assert hybrid_res.status_code == 200
    hybrid_jobs = hybrid_res.json()
    assert all(j["work_mode"] == "HYBRID" for j in hybrid_jobs)

    # 4. Get Job Details by ID
    job_id = pyspark_jobs[0]["id"]
    get_res = await async_client.get(f"/api/v1/jobs/{job_id}")
    assert get_res.status_code == 200
    assert get_res.json()["company"] == "CloudData Analytics"
