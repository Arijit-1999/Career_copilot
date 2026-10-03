"""APP-001: Form field mapper — maps detected HTML form fields to candidate profile data.

The mapper is intentionally heuristic-based (no LLM calls) so it is fast, deterministic,
and testable without any external dependencies.  The LLM gateway may be layered on top in
a future iteration for difficult fields.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Optional

from app.applications.enums import AutomationLevel
from app.applications.schemas import (
    DetectedFormField,
    FormMappingRequest,
    FormMappingResult,
    MappedFormField,
)


# ---------------------------------------------------------------------------
# Keyword → candidate profile field mappings
# ---------------------------------------------------------------------------

#: Maps lower-cased label/name keywords to dot-paths in a candidate profile dict.
_LABEL_KEYWORD_MAP: list[tuple[re.Pattern[str], str]] = [
    # Contact
    (re.compile(r"\bfull[\s_-]?name\b|full name"),          "full_name"),
    (re.compile(r"\bfirst[\s_-]?name\b"),                    "first_name"),
    (re.compile(r"\blast[\s_-]?name\b|surname"),             "last_name"),
    (re.compile(r"\bemail\b"),                               "email"),
    (re.compile(r"\bphone\b|\bmobile\b|\bcell\b"),           "phone"),
    (re.compile(r"\blinkedin\b"),                            "linkedin_url"),
    (re.compile(r"\bgithub\b"),                              "github_url"),
    (re.compile(r"\bportfolio\b|\bwebsite\b"),               "website_url"),
    (re.compile(r"\bcity\b|\blocation\b"),                   "city"),
    (re.compile(r"\bstate\b|\bprovince\b"),                  "state"),
    (re.compile(r"\bcountry\b"),                             "country"),
    # Professional
    (re.compile(r"\bcurrent[\s_-]?title\b|\bjob[\s_-]?title\b|\bdesignation\b"), "current_title"),
    (re.compile(r"\bcurrent[\s_-]?company\b|\bemployer\b"),  "current_company"),
    (re.compile(r"\byears[\s_-]?of[\s_-]?exp|\bexperience[\s_-]?years\b"),     "years_of_experience"),
    (re.compile(r"\bexpected[\s_-]?salary\b|\bcurrent[\s_-]?salary\b|\bctc\b"),  "expected_salary"),
    (re.compile(r"\bnotice[\s_-]?period\b"),                 "notice_period"),
    # Documents
    (re.compile(r"\bresume\b|\bcv\b"),                       "_resume_file"),   # special
    (re.compile(r"\bcover[\s_-]?letter\b"),                  "_cover_letter"),  # special
]

#: Sensitivity tokens — fields containing these should be flagged for human review.
_SENSITIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bsalary\b|\bctc\b|\bcompensation\b"),
    re.compile(r"\bssn\b|\bsocial[\s_-]?security\b|\bpassport\b|\bpan\b|\baadhaar\b"),
    re.compile(r"\bgender\b|\bethnic\b|\bdisabilit\b|\bveteran\b"),
    re.compile(r"\bsponsor\b|\bvisa\b|\bauthori[sz]ation\b"),
]

_CONFIDENCE_DIRECT_MAP = 0.95   # Keyword-matched and value present
_CONFIDENCE_PARTIAL_MAP = 0.60  # Matched but value empty/None
_CONFIDENCE_NONE = 0.0          # No match at all


def _is_sensitive(label: str, field_name: str) -> bool:
    text = f"{label} {field_name}".lower()
    return any(p.search(text) for p in _SENSITIVE_PATTERNS)


def _resolve_value(dot_path: str, profile: Dict[str, Any]) -> Optional[str]:
    """Walks dot-separated path into nested profile dict; returns None if missing."""
    if dot_path.startswith("_"):
        return None  # Special fields require human action
    parts = dot_path.split(".")
    node: Any = profile
    for part in parts:
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return str(node) if node is not None else None


def _match_field(field: DetectedFormField) -> tuple[Optional[str], Optional[str]]:
    """Returns (dot_path, matched_pattern_label) for the best matching keyword, or (None, None)."""
    search_text = f"{field.label} {field.field_name}".lower()
    for pattern, dot_path in _LABEL_KEYWORD_MAP:
        if pattern.search(search_text):
            return dot_path, dot_path
    return None, None


class FormFieldMapper:
    """
    Maps a list of detected HTML form fields to candidate profile values.

    Usage::

        mapper = FormFieldMapper(candidate_profile_dict)
        result = mapper.map(request)
    """

    def __init__(self, candidate_profile: Dict[str, Any]) -> None:
        self._profile = candidate_profile

    def map(self, request: FormMappingRequest) -> FormMappingResult:
        """Map all detected fields to candidate data and compute a routing recommendation."""
        mapped: list[MappedFormField] = []
        unmapped_required: list[str] = []
        total_confidence = 0.0
        count = 0

        for field in request.detected_fields:
            dot_path, _ = _match_field(field)
            sensitive = _is_sensitive(field.label, field.field_name)

            if dot_path is None:
                # No keyword match
                mapped_value = None
                confidence = _CONFIDENCE_NONE
                needs_review = field.required
                if field.required:
                    unmapped_required.append(field.field_name)
            else:
                mapped_value = _resolve_value(dot_path, self._profile)
                if mapped_value is not None:
                    confidence = _CONFIDENCE_DIRECT_MAP
                else:
                    confidence = _CONFIDENCE_PARTIAL_MAP
                    if field.required:
                        unmapped_required.append(field.field_name)
                needs_review = sensitive or confidence < _CONFIDENCE_PARTIAL_MAP

            mapped.append(
                MappedFormField(
                    field_name=field.field_name,
                    label=field.label,
                    field_type=field.field_type,
                    required=field.required,
                    mapped_value=mapped_value,
                    confidence=confidence,
                    needs_human_review=needs_review,
                )
            )
            total_confidence += confidence
            count += 1

        overall = round(total_confidence / count, 4) if count else 0.0
        recommendation = self._recommend(overall, unmapped_required, mapped)

        return FormMappingResult(
            candidate_id=request.candidate_id,
            job_id=request.job_id,
            mapped_fields=mapped,
            unmapped_required_fields=unmapped_required,
            overall_confidence=overall,
            automation_recommendation=recommendation,
        )

    @staticmethod
    def _recommend(
        overall: float,
        unmapped_required: list[str],
        mapped: list[MappedFormField],
    ) -> AutomationLevel:
        """Decide automation level based on mapping quality signals."""
        if unmapped_required:
            return AutomationLevel.HUMAN_REQUIRED
        review_count = sum(1 for f in mapped if f.needs_human_review)
        if review_count > 0 or overall < 0.75:
            return AutomationLevel.PARTIAL_AUTO
        return AutomationLevel.FULL_AUTO
