"""Unit tests for career search profiles and deterministic intent expansion."""

import pytest
from app.career_profiles.intent_agent import CareerIntentAgent
from app.career_profiles.schemas import CareerSearchProfileCreate, IntentExpansionRequest
from app.candidate.enums import WorkModePreference


def test_intent_expansion_python_backend():
    """Verify natural-language expansion for Python backend queries."""
    req = IntentExpansionRequest(query="I am looking for roles around Python, FastAPI, and PostgreSQL backend development")
    res = CareerIntentAgent.expand_intent(req.query)
    
    assert res.original_query == req.query
    assert "Python Backend Engineer" in res.primary_roles
    assert "FastAPI" in res.recommended_skills
    assert "PostgreSQL" in res.recommended_skills
    assert res.expansion_method == "deterministic_ontology"
    assert len(res.alternative_roles) > 0


def test_intent_expansion_aws_data():
    """Verify natural-language expansion for AWS data pipeline queries."""
    req = IntentExpansionRequest(query="I want to work with AWS data pipelines, S3, Glue, and PySpark ETL")
    res = CareerIntentAgent.expand_intent(req.query)
    
    assert "AWS Data Engineer" in res.primary_roles
    assert "PySpark" in res.recommended_skills
    assert any("Data" in alt for alt in res.alternative_roles)


def test_search_profile_schema():
    """Verify CareerSearchProfileCreate schema validations."""
    profile = CareerSearchProfileCreate(
        name="AWS Data & Python Track",
        target_roles=["AWS Data Engineer", "Python Backend Engineer"],
        alternative_roles=["Cloud Data Engineer"],
        required_skills=["Python", "AWS", "SQL"],
        preferred_skills=["Spark", "Airflow"],
        excluded_skills=["PHP", "Ruby"],
        locations=["Bengaluru", "Remote"],
        work_modes=[WorkModePreference.REMOTE, WorkModePreference.HYBRID],
        min_experience_years=3.0,
        min_salary=1800000.0,
        target_salary=2500000.0
    )
    assert profile.name == "AWS Data & Python Track"
    assert len(profile.target_roles) == 2
    assert len(profile.work_modes) == 2
    assert profile.min_experience_years == 3.0
