"""Unit tests for deterministic skill tagger, section parsing, and seniority detection."""

import pytest
from app.extraction.tagger import tagger
from app.extraction.enums import (
    SeniorityLevel,
    RequirementCategory,
    RequirementImportance
)


def test_infer_seniority():
    """Verify seniority inference across various title and JD patterns."""
    assert tagger.infer_seniority("Senior Backend Engineer", "We need Python") == SeniorityLevel.SENIOR
    assert tagger.infer_seniority("Lead AI Engineer", "Lead the core agentic team") == SeniorityLevel.LEAD
    assert tagger.infer_seniority("Principal Cloud Architect", "Design enterprise systems") == SeniorityLevel.PRINCIPAL
    assert tagger.infer_seniority("Staff Software Engineer", "Build infra") == SeniorityLevel.STAFF
    assert tagger.infer_seniority("Junior Python Developer", "Fresh graduate welcome") == SeniorityLevel.JUNIOR
    assert tagger.infer_seniority("Software Engineering Intern", "Summer internship") == SeniorityLevel.INTERN
    assert tagger.infer_seniority("VP of Engineering", "Lead entire engineering dept") == SeniorityLevel.DIRECTOR


def test_experience_range_extraction():
    """Verify numeric experience extraction from text."""
    min_exp, max_exp = tagger.extract_experience_range("Requires 4-7 years of experience in Python.")
    assert min_exp == 4.0
    assert max_exp == 7.0

    min_exp2, max_exp2 = tagger.extract_experience_range("Must have at least 5+ years building backend systems.")
    assert min_exp2 == 5.0
    assert max_exp2 is None


def test_section_segmentation():
    """Verify splitting JD text into distinct sections."""
    jd_text = """
    The Role:
    Build high-scale microservices.
    
    Requirements:
    - 5+ years Python and FastAPI
    - Deep knowledge of PostgreSQL and Docker
    
    Preferred Qualifications:
    - Experience with pgvector and LangChain
    - AWS and Terraform expertise
    """
    sections = tagger.segment_sections(jd_text)
    assert "FastAPI" in sections["mandatory"]
    assert "LangChain" in sections["preferred"]
    assert "microservices" in sections["responsibilities"]


def test_analyze_jd_full():
    """Verify complete zero-token JD analysis and skill classification."""
    title = "Senior AI Backend Engineer (Python / FastAPI)"
    jd_text = """
    Responsibilities:
    • Build low latency AI agents and microservices.
    • Optimize vector database queries and retrieval pipelines.

    Requirements:
    • 4 to 6 years of experience.
    • Strong proficiency in Python, FastAPI, and PostgreSQL.
    • Solid understanding of Docker and CI/CD.

    Nice to Have:
    • Hands-on experience with pgvector, LangChain, or Qdrant.
    • Cloud deployment experience with AWS.
    """
    result = tagger.analyze_jd(title=title, description=jd_text)

    assert result.seniority == SeniorityLevel.SENIOR
    assert result.min_experience_years == 4.0
    assert result.max_experience_years == 6.0

    # Verify mandatory skills
    assert "Python" in result.required_skills
    assert "FastAPI" in result.required_skills
    assert "PostgreSQL" in result.required_skills
    assert "Docker" in result.required_skills

    # Verify preferred skills
    assert "LangChain" in result.preferred_skills
    assert "AWS" in result.preferred_skills

    # Verify domains and tags
    assert "AI & Machine Learning" in result.domains
    assert "Backend Engineering" in result.domains
    assert "Cloud & Infrastructure" in result.domains
    assert len(result.responsibilities) >= 1


def test_education_extraction():
    """Verify education extraction from various JD formats."""
    text1 = "Must have a Bachelor's degree in Computer Science or related STEM field."
    edu1 = tagger.extract_education(text1)
    assert any("Bachelor" in e for e in edu1)

    text2 = "Preferred: Master's or PhD in AI/ML or Computer Science."
    edu2 = tagger.extract_education(text2)
    assert any("Master" in e for e in edu2)
    assert any("PhD" in e for e in edu2)

