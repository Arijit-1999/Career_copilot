"""Unit tests for multi-stage deterministic matching engine, hard filters, and explainability."""

import pytest
import uuid
from datetime import date
from app.candidate.models import CandidateProfile, CandidateSkill, Skill, CandidateExperience
from app.candidate.enums import SkillState, WorkModePreference
from app.career_profiles.models import CareerSearchProfile
from app.jobs.models import Job
from app.matching.engine import matching_engine
from app.matching.enums import MatchStatus, FilterRejectionReason


def create_sample_candidate():
    profile = CandidateProfile(
        id=uuid.uuid4(),
        full_name="Alex River",
        email="alex@example.com",
        current_title="Senior Python Backend Engineer",
        target_roles=["Senior Python Engineer", "Backend Architect"],
        work_mode=WorkModePreference.FLEXIBLE,
        location="Bangalore",
        min_salary=25.0,
        currency="INR"
    )
    
    # 5 years experience
    exp = CandidateExperience(
        id=uuid.uuid4(),
        candidate_id=profile.id,
        company="ScaleTech",
        title="Senior Backend Engineer",
        start_date=date(2019, 1, 1),
        end_date=date(2024, 1, 1),
        is_current=False
    )
    profile.experiences = [exp]

    # Skills: Python (Verified), FastAPI (Verified), PostgreSQL (Claimed), Docker (Learning)
    s_python = Skill(id="python", name="Python", canonical_name="python")
    s_fastapi = Skill(id="fastapi", name="FastAPI", canonical_name="fastapi")
    s_postgres = Skill(id="postgresql", name="PostgreSQL", canonical_name="postgresql")
    s_docker = Skill(id="docker", name="Docker", canonical_name="docker")

    profile.skills = [
        CandidateSkill(candidate_id=profile.id, skill_id="python", state=SkillState.VERIFIED, skill=s_python),
        CandidateSkill(candidate_id=profile.id, skill_id="fastapi", state=SkillState.VERIFIED, skill=s_fastapi),
        CandidateSkill(candidate_id=profile.id, skill_id="postgresql", state=SkillState.CLAIMED, skill=s_postgres),
        CandidateSkill(candidate_id=profile.id, skill_id="docker", state=SkillState.LEARNING, skill=s_docker)
    ]

    return profile


def test_hard_filters_pass_on_matching_job():
    candidate = create_sample_candidate()
    job = Job(
        id=uuid.uuid4(),
        title="Senior Python Engineer",
        normalized_title="Senior Python Engineer",
        company="TechCorp",
        location="Bangalore",
        work_mode=WorkModePreference.HYBRID,
        min_experience_years=4.0,
        max_experience_years=7.0,
        required_skills=["Python", "FastAPI"],
        preferred_skills=["PostgreSQL", "Docker"]
    )

    passed, reasons = matching_engine.evaluate_hard_filters(
        candidate=candidate,
        job=job,
        candidate_experience_years=5.0
    )
    assert passed is True
    assert len(reasons) == 0


def test_hard_filters_fail_on_work_mode_and_location():
    candidate = create_sample_candidate()
    # Search profile strictly wanting Remote
    sp = CareerSearchProfile(
        candidate_id=candidate.id,
        name="Remote Only",
        target_roles=["Python Engineer"],
        locations=["Remote"],
        work_modes=["REMOTE"]
    )

    job = Job(
        id=uuid.uuid4(),
        title="Python Engineer",
        normalized_title="Python Engineer",
        company="Onsite Labs",
        location="Mumbai",
        work_mode=WorkModePreference.ONSITE,
        min_experience_years=3.0
    )

    passed, reasons = matching_engine.evaluate_hard_filters(
        candidate=candidate,
        job=job,
        search_profile=sp,
        candidate_experience_years=5.0
    )
    assert passed is False
    assert FilterRejectionReason.WORK_MODE_MISMATCH in reasons


def test_hard_filters_experience_bounds():
    candidate = create_sample_candidate()
    
    # Job requires 8+ years (candidate has 5.0 -> deficit 3.0 > 1.0 grace margin)
    job_senior = Job(
        id=uuid.uuid4(),
        title="Director of Engineering",
        normalized_title="Director of Engineering",
        company="MegaCorp",
        location="Remote",
        work_mode=WorkModePreference.REMOTE,
        min_experience_years=8.0
    )

    passed, reasons = matching_engine.evaluate_hard_filters(
        candidate=candidate,
        job=job_senior,
        candidate_experience_years=5.0
    )
    assert passed is False
    assert FilterRejectionReason.EXPERIENCE_TOO_LOW in reasons


def test_skill_evaluation_and_gaps():
    candidate = create_sample_candidate()
    
    score, matched, missing_mand, missing_pref, details = matching_engine.evaluate_skills(
        candidate_skills=candidate.skills,
        job_required=["Python", "FastAPI", "Kubernetes"],
        job_preferred=["PostgreSQL", "Terraform"]
    )

    # Matched Python (Verified=1.0) + FastAPI (Verified=1.0)
    assert "Python" in matched
    assert "FastAPI" in matched
    assert "PostgreSQL" in matched
    # Missing required: Kubernetes
    assert "Kubernetes" in missing_mand
    # Missing preferred: Terraform
    assert "Terraform" in missing_pref
    assert score >= 50.0


def test_full_match_pipeline_explainability():
    candidate = create_sample_candidate()
    job = Job(
        id=uuid.uuid4(),
        title="Senior Python Backend Engineer",
        normalized_title="Senior Python Backend Engineer",
        company="InnovateAI",
        location="Bangalore",
        work_mode=WorkModePreference.FLEXIBLE,
        min_experience_years=4.0,
        max_experience_years=6.0,
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        preferred_skills=["Docker"]
    )

    breakdown = matching_engine.match(candidate=candidate, job=job)

    assert breakdown.passed_hard_filters is True
    assert breakdown.overall_score >= 80.0
    assert len(breakdown.matched_skills) >= 3
    assert len(breakdown.highlights) >= 2
    assert breakdown.reasoning_summary is not None
