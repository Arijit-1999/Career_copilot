"""Unit tests for candidate schemas and skill state transitions."""

import pytest
from app.candidate.enums import SkillState, FactType, FactVerificationStatus, WorkModePreference
from app.candidate.schemas import (
    CandidateProfileCreate,
    CandidateSkillCreate,
    ResumeFactCreate
)


def test_candidate_profile_schema_validation():
    """Verify CandidateProfileCreate schema validation and defaults."""
    profile = CandidateProfileCreate(
        full_name="Arijit Test",
        email="arijit@example.com",
        current_title="Senior Python Engineer",
        target_roles=["Python Backend Engineer", "AWS Data Engineer"],
        work_mode=WorkModePreference.REMOTE
    )
    assert profile.full_name == "Arijit Test"
    assert profile.email == "arijit@example.com"
    assert profile.currency == "INR"
    assert profile.work_mode == WorkModePreference.REMOTE
    assert len(profile.target_roles) == 2


def test_candidate_skill_state_defaults():
    """Verify CandidateSkillCreate defaults to CLAIMED state."""
    skill = CandidateSkillCreate(
        skill_name="FastAPI",
        category="Frameworks"
    )
    assert skill.skill_name == "FastAPI"
    assert skill.state == SkillState.CLAIMED
    assert skill.confidence_level == 3


def test_resume_fact_schema():
    """Verify ResumeFactCreate schema properties."""
    fact = ResumeFactCreate(
        fact_type=FactType.METRIC,
        title="Optimized API response time",
        description="Reduced database latency by 45% through pgvector indexing",
        metrics={"latency_reduction_pct": 45},
        verification_status=FactVerificationStatus.VERIFIED,
        tags=["performance", "database"]
    )
    assert fact.fact_type == FactType.METRIC
    assert fact.verification_status == FactVerificationStatus.VERIFIED
    assert fact.metrics["latency_reduction_pct"] == 45
