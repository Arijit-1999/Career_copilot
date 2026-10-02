"""Unit tests for Job Normalization, Salary Parsing, Freshness, and Deduplication."""

import pytest
from datetime import datetime, timezone, timedelta
from app.jobs.normalization import (
    clean_text,
    canonicalize_url,
    normalize_title,
    parse_salary,
    classify_work_mode,
    calculate_freshness
)
from app.jobs.deduplication import generate_content_hash
from app.candidate.enums import WorkModePreference
from app.jobs.enums import JobFreshness


def test_clean_text():
    """Verify HTML stripping and whitespace normalization."""
    html_text = "<p>We are hiring a <strong>Senior Python Developer</strong>.&nbsp;Apply now!</p>"
    cleaned = clean_text(html_text)
    assert "<p>" not in cleaned
    assert "<strong>" not in cleaned
    assert "Senior Python Developer" in cleaned
    assert "&nbsp;" not in cleaned


def test_canonicalize_url():
    """Verify removal of tracking query parameters."""
    raw_url = "https://www.linkedin.com/jobs/view/123456789/?utm_source=share&utm_medium=member_desktop&refId=abc12345"
    clean_url = canonicalize_url(raw_url)
    assert clean_url == "https://www.linkedin.com/jobs/view/123456789"
    assert "utm_source" not in clean_url
    assert "refId" not in clean_url


def test_normalize_title():
    """Verify removal of promotional tags and brackets."""
    title_1 = "[Urgent] Senior Python Backend Developer (Immediate Joiner)"
    title_2 = "Lead Data Engineer - Remote / Hybrid"
    assert normalize_title(title_1) == "Senior Python Backend Developer"
    assert "Remote" not in normalize_title(title_2)


def test_parse_salary():
    """Verify Indian LPA and standard currency parsing."""
    # Indian LPA Range
    min_sal, max_sal, curr = parse_salary("₹18L - ₹28L")
    assert min_sal == 1800000.0
    assert max_sal == 2800000.0
    assert curr == "INR"

    # Single LPA
    min_sal, max_sal, curr = parse_salary("25 LPA")
    assert min_sal == 2500000.0
    assert max_sal == 2500000.0

    # USD Range
    min_sal, max_sal, curr = parse_salary("$120k - $160k")
    assert min_sal == 120000.0
    assert max_sal == 160000.0
    assert curr == "USD"


def test_classify_work_mode():
    """Verify work mode classification heuristics."""
    mode_remote = classify_work_mode("Bengaluru (Remote)", "Python Engineer", "Work from anywhere in India")
    mode_hybrid = classify_work_mode("Bengaluru", "AWS Engineer", "Requires 2 days in office and hybrid work")
    mode_onsite = classify_work_mode("Mumbai", "System Administrator", "100% On-site position in Mumbai office")

    assert mode_remote == WorkModePreference.REMOTE
    assert mode_hybrid == WorkModePreference.HYBRID
    assert mode_onsite == WorkModePreference.ONSITE


def test_calculate_freshness():
    """Verify freshness scoring against timestamps."""
    now = datetime.now(timezone.utc)
    fresh_time = now - timedelta(hours=6)
    older_time = now - timedelta(days=10)
    expired_time = now - timedelta(days=20)

    assert calculate_freshness(fresh_time, now) == JobFreshness.VERY_FRESH
    assert calculate_freshness(older_time, now) == JobFreshness.OLDER
    assert calculate_freshness(expired_time, now) == JobFreshness.LOW_PRIORITY


def test_generate_content_hash():
    """Verify SHA-256 content hash determinism and sensitivity."""
    hash_1 = generate_content_hash("Google", "Senior Software Engineer", "Looking for backend engineers.")
    hash_2 = generate_content_hash("Google", "Senior Software Engineer", "Looking for backend engineers.")
    hash_3 = generate_content_hash("Meta", "Senior Software Engineer", "Looking for backend engineers.")

    assert hash_1 == hash_2
    assert hash_1 != hash_3
    assert len(hash_1) == 64
