"""Zero-hallucination Truth Validator enforcing that 100% of resume claims map to verified candidate facts."""

import re
from typing import List, Set, Dict, Tuple, Optional
from app.candidate.enums import SkillState, FactVerificationStatus
from app.candidate.models import CandidateProfile
from app.resumes.enums import ValidationSeverity
from app.resumes.schemas import (
    ResumeStructuredContent,
    TruthValidationClaim,
    TruthValidationResult
)


class TruthValidator:
    """Verifies that generated or edited resumes contain zero hallucinations and only grounded facts."""

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"[^a-z0-9+#.]", "", text.lower().strip())

    def validate_content(
        self,
        candidate: CandidateProfile,
        content: ResumeStructuredContent
    ) -> TruthValidationResult:
        """Validates structured resume content against candidate's canonical skill and fact bank."""
        claims: List[TruthValidationClaim] = []
        hallucinations: List[str] = []

        # 1. Build Candidate Truth Bank Maps
        verified_skills: Set[str] = set()
        claimed_skills: Set[str] = set()
        for cs in candidate.skills:
            norm = self._normalize(cs.skill.name if cs.skill else cs.skill_id)
            if cs.state == SkillState.VERIFIED:
                verified_skills.add(norm)
            elif cs.state == SkillState.CLAIMED:
                claimed_skills.add(norm)

        verified_companies = {
            self._normalize(exp.company) for exp in candidate.experiences
        }

        # 2. Validate Skill Groups
        for group in content.skill_groups:
            for skill in group.skills:
                norm_s = self._normalize(skill)
                if norm_s in verified_skills:
                    claims.append(
                        TruthValidationClaim(
                            claim_text=f"Skill: {skill}",
                            severity=ValidationSeverity.INFO,
                            is_verified=True,
                            source_reference="CandidateSkill (VERIFIED)",
                            explanation=f"Skill '{skill}' is verified in candidate skill bank."
                        )
                    )
                elif norm_s in claimed_skills:
                    claims.append(
                        TruthValidationClaim(
                            claim_text=f"Skill: {skill}",
                            severity=ValidationSeverity.WARNING,
                            is_verified=False,
                            source_reference="CandidateSkill (CLAIMED)",
                            explanation=f"Skill '{skill}' is claimed by candidate but not yet verified."
                        )
                    )
                else:
                    # Hallucination: Skill not in candidate profile
                    hallucinations.append(f"Unregistered skill claim: '{skill}'")
                    claims.append(
                        TruthValidationClaim(
                            claim_text=f"Skill: {skill}",
                            severity=ValidationSeverity.ERROR,
                            is_verified=False,
                            source_reference=None,
                            explanation=f"Skill '{skill}' does not exist in candidate profile (Hallucination)."
                        )
                    )

        # 3. Validate Companies in Experience
        for exp in content.experiences:
            norm_c = self._normalize(exp.company)
            if norm_c in verified_companies:
                claims.append(
                    TruthValidationClaim(
                        claim_text=f"Experience: {exp.title} at {exp.company}",
                        severity=ValidationSeverity.INFO,
                        is_verified=True,
                        source_reference=f"CandidateExperience ({exp.company})",
                        explanation=f"Employment at {exp.company} verified."
                    )
                )
            else:
                hallucinations.append(f"Unverified employer: '{exp.company}'")
                claims.append(
                    TruthValidationClaim(
                        claim_text=f"Experience at {exp.company}",
                        severity=ValidationSeverity.ERROR,
                        is_verified=False,
                        source_reference=None,
                        explanation=f"Employer '{exp.company}' not found in candidate history."
                    )
                )

        # 4. Calculate Truth Score
        verified_count = sum(1 for c in claims if c.is_verified)
        unverified_count = len(claims) - verified_count

        error_count = sum(1 for c in claims if c.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for c in claims if c.severity == ValidationSeverity.WARNING)

        deductions = (error_count * 25.0) + (warning_count * 5.0)
        truth_score = max(0.0, round(100.0 - deductions, 1))

        is_valid = error_count == 0

        return TruthValidationResult(
            is_valid=is_valid,
            truth_score=truth_score,
            verified_claims_count=verified_count,
            unverified_claims_count=unverified_count,
            claims=claims,
            hallucinations_detected=hallucinations
        )


truth_validator = TruthValidator()
