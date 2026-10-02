"""Normalization utilities for job descriptions, URLs, titles, salaries, and freshness."""

import html
import re
from urllib.parse import urlparse, urlunparse
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from app.candidate.enums import WorkModePreference
from app.jobs.enums import JobFreshness
from app.common.models import utc_now


def clean_text(text: str) -> str:
    """Strips HTML tags, converts HTML entities, collapses excessive whitespace, and normalizes unicode."""
    if not text:
        return ""
    # Unescape HTML entities (like &nbsp;, &amp;, &lt;, &gt;)
    unescaped = html.unescape(text)
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", unescaped)
    # Replace non-breaking spaces and special quotes
    cleaned = cleaned.replace("\xa0", " ").replace("’", "'").replace("“", '"').replace("”", '"')
    # Collapse multiple whitespaces/newlines
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned)
    return cleaned.strip()


def canonicalize_url(url: Optional[str]) -> Optional[str]:
    """Removes tracking query parameters (utm_*, refId, trk, etc.) and normalizes URL."""
    if not url:
        return None
    try:
        parsed = urlparse(url.strip())
        if not parsed.scheme or not parsed.netloc:
            return url.strip()
        # Keep path without trailing slash (unless root)
        path = parsed.path.rstrip("/") if len(parsed.path) > 1 else parsed.path
        # Clean URL without tracking query parameters
        return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))
    except Exception:
        return url.strip()


def normalize_title(title: str) -> str:
    """Normalizes job titles by removing promotional prefixes, brackets, and trailing tags."""
    if not title:
        return ""
    # Remove leading brackets like [Urgent], (Immediate Joiner), [Remote]
    cleaned = re.sub(r"^[\[\(][^\]\)]+[\]\)]\s*", "", title)
    # Remove bracketed buzzwords anywhere in the title
    cleaned = re.sub(r"\s*[\[\(][^\]\)]*(?:urgent|immediate joiner|hiring|remote|hybrid|joiner|wfh)[^\]\)]*[\]\)]", "", cleaned, flags=re.IGNORECASE)
    # Iteratively strip trailing tags like "- Remote / Hybrid" or "| Urgent"
    while True:
        prev = cleaned
        cleaned = re.sub(r"\s*[-|/]\s*(?:remote|hybrid|immediate|urgent|joiner|hiring|wfh|full[- ]time|onsite|on-site)\s*$", "", cleaned, flags=re.IGNORECASE)
        if cleaned == prev:
            break
    return re.sub(r"\s+", " ", cleaned).strip()


def parse_salary(
    salary_raw: Optional[str], default_currency: str = "INR"
) -> Tuple[Optional[float], Optional[float], str]:
    """Extracts numeric minimum and maximum salary from unstructured text."""
    if not salary_raw:
        return None, None, default_currency

    text = salary_raw.upper().replace(",", "").strip()
    currency = default_currency
    if "$" in text or "USD" in text:
        currency = "USD"
    elif "€" in text or "EUR" in text:
        currency = "EUR"
    elif "£" in text or "GBP" in text:
        currency = "GBP"
    elif "₹" in text or "INR" in text or "LPA" in text or "LAKH" in text or "LAC" in text:
        currency = "INR"

    # Match Indian LPA/Lakhs range: e.g. "₹18L - ₹28L", "15 - 25 LPA", "20L - 30L", "18-24 Lakhs"
    lpa_range = re.search(
        r"(?:₹|INR)?\s*(\d+(?:\.\d+)?)\s*(?:LPA|LAKHS|LAKH|LAC|L)?\s*(?:-|TO|\s+TO\s+)\s*(?:₹|INR)?\s*(\d+(?:\.\d+)?)\s*(?:LPA|LAKHS|LAKH|LAC|L)",
        text,
    )
    if lpa_range:
        min_val = float(lpa_range.group(1)) * 100000.0
        max_val = float(lpa_range.group(2)) * 100000.0
        return min_val, max_val, "INR"

    single_lpa = re.search(r"(?:₹|INR)?\s*(\d+(?:\.\d+)?)\s*(?:LPA|LAKHS|LAKH|LAC|L)", text)
    if single_lpa:
        val = float(single_lpa.group(1)) * 100000.0
        return val, val, "INR"

    # Match standard 'K' range: e.g. "$50k - $80k", "50k - 80k"
    k_range = re.search(
        r"(?:\$|€|£)?\s*(\d+(?:\.\d+)?)\s*K\s*(?:-|TO)\s*(?:\$|€|£)?\s*(\d+(?:\.\d+)?)\s*K", text
    )
    if k_range:
        return float(k_range.group(1)) * 1000.0, float(k_range.group(2)) * 1000.0, currency

    single_k = re.search(r"(?:\$|€|£)?\s*(\d+(?:\.\d+)?)\s*K", text)
    if single_k:
        val = float(single_k.group(1)) * 1000.0
        return val, val, currency

    # Match standard numeric range: e.g. "120000 - 150000"
    std_range = re.search(r"(\d{4,9})\s*(?:-|TO)\s*(\d{4,9})", text)
    if std_range:
        return float(std_range.group(1)), float(std_range.group(2)), currency

    return None, None, currency


def classify_work_mode(
    location: str, title: str, description: str, explicit_mode: Optional[WorkModePreference] = None
) -> WorkModePreference:
    """Infers work mode (REMOTE, HYBRID, ONSITE) from job attributes."""
    if explicit_mode:
        return explicit_mode

    combined = f"{location} {title} {description[:300]}".upper()

    if "REMOTE" in combined or "WORK FROM HOME" in combined or "WFH" in combined:
        if "HYBRID" in combined:
            return WorkModePreference.HYBRID
        return WorkModePreference.REMOTE
    elif "HYBRID" in combined:
        return WorkModePreference.HYBRID
    elif "ONSITE" in combined or "ON-SITE" in combined or "IN-OFFICE" in combined:
        return WorkModePreference.ONSITE

    return WorkModePreference.FLEXIBLE


def calculate_freshness(
    posted_at: Optional[datetime], first_seen_at: datetime
) -> JobFreshness:
    """Scores job freshness based on reference timestamp against current time."""
    ref_time = posted_at if posted_at else first_seen_at
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)
    
    now = utc_now()
    age = now - ref_time

    if age <= timedelta(hours=24):
        return JobFreshness.VERY_FRESH
    elif age <= timedelta(days=3):
        return JobFreshness.FRESH
    elif age <= timedelta(days=7):
        return JobFreshness.RECENT
    elif age <= timedelta(days=14):
        return JobFreshness.OLDER
    else:
        return JobFreshness.LOW_PRIORITY
