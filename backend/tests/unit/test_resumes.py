"""Unit tests for Fact Selector, Truth Validator, and Resume Generator."""

import pytest
import uuid
from datetime import date
from app.candidate.models import (
    CandidateProfile,
    CandidateSkill,
    Skill,
    ResumeFact,
    CandidateExperience,
    CandidateProject
)
from app.candidate.enums import SkillState, FactType, FactVerificationStatus
from app.jobs.models import Job
from app.resumes.fact_selector import fact_selector
from app.resumes.validator import truth_validator
from app.resumes.generator import resume_generator
from app.resumes.schemas import ResumeStructuredContent, ResumeSectionHeader, ResumeSkillGroup, ResumeExperienceItem


def create_candidate_with_facts():
    candidate = CandidateProfile(
        id=uuid.uuid4(),
        full_name="Taylor Swift-Developer",
        email="taylor@example.com",
        phone="+1-555-0199",
        location="San Francisco, CA",
        current_title="Lead AI Engineer"
    )

    s_python = Skill(id="python", name="Python", canonical_name="python")
    s_fastapi = Skill(id="fastapi", name="FastAPI", canonical_name="fastapi")
    s_pgvector = Skill(id="pgvector", name="pgvector", canonical_name="pgvector")
    s_k8s = Skill(id="k8s", name="Kubernetes", canonical_name="k8s")

    candidate.skills = [
        CandidateSkill(candidate_id=candidate.id, skill_id="python", state=SkillState.VERIFIED, skill=s_python),
        CandidateSkill(candidate_id=candidate.id, skill_id="fastapi", state=SkillState.VERIFIED, skill=s_fastapi),
        CandidateSkill(candidate_id=candidate.id, skill_id="pgvector", state=SkillState.VERIFIED, skill=s_pgvector),
        CandidateSkill(candidate_id=candidate.id, skill_id="k8s", state=SkillState.CLAIMED, skill=s_k8s)
    ]

    exp = CandidateExperience(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        company="VectorTech Labs",
        title="Senior AI Platform Engineer",
        location="San Francisco",
        start_date=date(2021, 6, 1),
        is_current=True,
        description="Engineered high-scale retrieval pipelines."
    )
    candidate.experiences = [exp]

    fact1 = ResumeFact(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        fact_type=FactType.ACHIEVEMENT,
        title="Vector Search Optimization",
        description="Reduced semantic search retrieval latency by 45% using pgvector HNSW indexing.",
        metrics={"latency_pct": 45},
        source_reference="VectorTech Labs",
        verification_status=FactVerificationStatus.VERIFIED,
        tags=["pgvector", "python", "optimization"]
    )
    candidate.facts = [fact1]

    proj = CandidateProject(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        name="Career Copilot AI",
        role="Creator",
        description="Personal AI Agent for job matching.",
        tech_stack=["Python", "FastAPI", "PostgreSQL", "pgvector"]
    )
    candidate.projects = [proj]

    return candidate


def test_fact_selector_prioritizes_jd_skills():
    candidate = create_candidate_with_facts()
    job = Job(
        id=uuid.uuid4(),
        title="AI Engineer",
        normalized_title="AI Engineer",
        company="DeepMind Labs",
        required_skills=["pgvector", "Python"],
        preferred_skills=["FastAPI"]
    )

    skill_groups, targeted = fact_selector.select_skills_for_jd(
        candidate_skills=candidate.skills,
        job=job,
        include_claimed=False
    )

    # Kubernetes is CLAIMED, so strictly excluded when include_claimed=False
    all_selected = [s for g in skill_groups for s in g.skills]
    assert "pgvector" in all_selected
    assert "Python" in all_selected
    assert "Kubernetes" not in all_selected
    assert "pgvector" in targeted


def test_truth_validator_detects_hallucinations():
    candidate = create_candidate_with_facts()

    # Create content with a hallucinated skill (Rust) and unverified company
    content = ResumeStructuredContent(
        header=ResumeSectionHeader(full_name=candidate.full_name, email=candidate.email),
        summary="Experienced engineer.",
        skill_groups=[
            ResumeSkillGroup(category_name="Languages", skills=["Python", "Rust"])  # Rust is hallucination
        ],
        experiences=[
            ResumeExperienceItem(
                company="FakeCompany Inc",  # Fake company
                title="Lead",
                start_date="2020",
                end_date="2021",
                bullets=["Did stuff"]
            )
        ]
    )

    result = truth_validator.validate_content(candidate, content)
    assert result.is_valid is False
    assert result.truth_score < 60.0
    assert len(result.hallucinations_detected) >= 2
    assert any("Rust" in h for h in result.hallucinations_detected)
    assert any("FakeCompany" in h for h in result.hallucinations_detected)


def test_truth_validator_passes_truthful_content():
    candidate = create_candidate_with_facts()

    content, targeted = fact_selector.select_structured_content(candidate, job=None, include_claimed=False)
    result = truth_validator.validate_content(candidate, content)

    assert result.is_valid is True
    assert result.truth_score == 100.0
    assert len(result.hallucinations_detected) == 0


def test_resume_markdown_rendering():
    candidate = create_candidate_with_facts()
    content, _ = fact_selector.select_structured_content(candidate, job=None, include_claimed=False)
    md = resume_generator.render_markdown(content)

    assert f"# {candidate.full_name}" in md
    assert "## Core Technical Competencies" in md
    assert "## Professional Experience" in md
    assert "VectorTech Labs" in md
    assert "Vector Search Optimization" in md
