"""Deterministic, multi-stage candidate-job matching engine with explainability."""

import re
from typing import List, Dict, Tuple, Optional, Set
from app.candidate.enums import SkillState, WorkModePreference
from app.candidate.models import CandidateProfile, CandidateSkill, CandidateExperience
from app.career_profiles.models import CareerSearchProfile
from app.jobs.models import Job
from app.matching.enums import MatchStatus, FilterRejectionReason
from app.matching.schemas import SkillMatchItem, MatchScoreBreakdown


class MatchingEngine:
    """Zero-hallucination deterministic matching engine evaluating candidates against jobs."""

    @staticmethod
    def _normalize_skill_key(name: str) -> str:
        """Normalizes skill name for reliable canonical lookup."""
        return re.sub(r"[^a-z0-9+#.]", "", name.lower().strip())

    @staticmethod
    def calculate_candidate_total_experience(candidate: CandidateProfile) -> float:
        """Calculates total estimated years of experience from experience history."""
        if not candidate.experiences:
            return 0.0

        total_months = 0
        from datetime import date
        today = date.today()

        for exp in candidate.experiences:
            start = exp.start_date
            end = exp.end_date if (exp.end_date and not exp.is_current) else today
            if start and end and end >= start:
                months = (end.year - start.year) * 12 + (end.month - start.month)
                total_months += max(1, months)

        return round(total_months / 12.0, 1)

    def evaluate_hard_filters(
        self,
        candidate: CandidateProfile,
        job: Job,
        search_profile: Optional[CareerSearchProfile] = None,
        candidate_experience_years: float = 0.0
    ) -> Tuple[bool, List[FilterRejectionReason]]:
        """Stage 1: Evaluates hard constraints (location, work mode, experience boundaries)."""
        rejection_reasons: List[FilterRejectionReason] = []

        # 1. Location & Work Mode Filter
        job_loc = (job.location or "").lower()
        job_work_mode = job.work_mode

        # Check work mode preference
        target_work_modes = []
        target_locations = []

        if search_profile:
            target_work_modes = [wm.upper() for wm in search_profile.work_modes]
            target_locations = [loc.lower() for loc in search_profile.locations]
        elif candidate.work_mode:
            target_work_modes = [candidate.work_mode.value.upper()]
            if candidate.location:
                target_locations = [candidate.location.lower()]

        # If candidate strictly wants REMOTE and job is ONSITE and not remote location
        if (
            "REMOTE" in target_work_modes
            and len(target_work_modes) == 1
            and job_work_mode == WorkModePreference.ONSITE
            and "remote" not in job_loc
        ):
            rejection_reasons.append(FilterRejectionReason.WORK_MODE_MISMATCH)

        # Location check if job is not remote
        if "remote" not in job_loc and job_work_mode != WorkModePreference.REMOTE and target_locations:
            matched_loc = any(
                loc in job_loc or job_loc in loc for loc in target_locations
            )
            if not matched_loc and "any" not in target_locations and "flexible" not in target_locations:
                rejection_reasons.append(FilterRejectionReason.LOCATION_MISMATCH)

        # 2. Experience Filter (with a 1.0 year grace buffer)
        job_min_exp = job.min_experience_years or 0.0
        if job_min_exp > 0 and candidate_experience_years < max(0.0, job_min_exp - 1.0):
            rejection_reasons.append(FilterRejectionReason.EXPERIENCE_TOO_LOW)

        job_max_exp = job.max_experience_years
        if job_max_exp and job_max_exp > 0 and candidate_experience_years > (job_max_exp + 3.0):
            rejection_reasons.append(FilterRejectionReason.EXPERIENCE_TOO_HIGH)

        # 3. Excluded Skills Filter
        if search_profile and search_profile.excluded_skills:
            excluded_set = {self._normalize_skill_key(s) for s in search_profile.excluded_skills}
            job_req_set = {self._normalize_skill_key(s) for s in (job.required_skills or [])}
            if excluded_set & job_req_set:
                rejection_reasons.append(FilterRejectionReason.EXCLUDED_SKILL_PRESENT)

        # 4. Salary Floor Check
        candidate_min_sal = (
            search_profile.min_salary if (search_profile and search_profile.min_salary)
            else candidate.min_salary
        )
        if (
            candidate_min_sal
            and job.salary_max
            and job.currency == (search_profile.currency if search_profile else candidate.currency)
            and job.salary_max < (candidate_min_sal * 0.85)
        ):
            rejection_reasons.append(FilterRejectionReason.SALARY_BELOW_MIN)

        passed = len(rejection_reasons) == 0
        return passed, rejection_reasons

    def evaluate_skills(
        self,
        candidate_skills: List[CandidateSkill],
        job_required: List[str],
        job_preferred: List[str]
    ) -> Tuple[float, List[str], List[str], List[str], List[SkillMatchItem]]:
        """Stage 2: Skill Overlap & Gap Matrix with state-weighted credits."""
        candidate_skill_map: Dict[str, Tuple[SkillState, str]] = {}
        for cs in candidate_skills:
            norm_key = self._normalize_skill_key(cs.skill.canonical_name if cs.skill else cs.skill_id)
            state = cs.state or SkillState.CLAIMED
            display = cs.skill.name if cs.skill else cs.skill_id
            candidate_skill_map[norm_key] = (state, display)

        skill_details: List[SkillMatchItem] = []
        matched_skills: Set[str] = set()
        missing_mandatory: List[str] = []
        missing_preferred: List[str] = []

        total_req_points = 0.0
        earned_req_points = 0.0
        total_pref_points = 0.0
        earned_pref_points = 0.0

        # State credit weights: VERIFIED = 1.0, CLAIMED = 0.75, LEARNING = 0.35, TARGET = 0.1
        state_weight = {
            SkillState.VERIFIED: 1.0,
            SkillState.CLAIMED: 0.75,
            SkillState.LEARNING: 0.35,
            SkillState.TARGET: 0.1,
            SkillState.NOT_RELEVANT: 0.0
        }

        # 1. Evaluate Required Skills
        for req in job_required:
            norm_req = self._normalize_skill_key(req)
            total_req_points += 1.0

            matched_item = None
            # Check exact or partial match
            for cand_norm, (cand_state, cand_name) in candidate_skill_map.items():
                if norm_req == cand_norm or norm_req in cand_norm or cand_norm in norm_req:
                    matched_item = (cand_state, cand_name)
                    break

            if matched_item:
                c_state, c_name = matched_item
                credit = state_weight.get(c_state, 0.75)
                earned_req_points += credit
                matched_skills.add(c_name)
                skill_details.append(
                    SkillMatchItem(
                        skill_name=req,
                        is_mandatory=True,
                        is_matched=True,
                        candidate_state=c_state,
                        weight_credit=credit
                    )
                )
            else:
                missing_mandatory.append(req)
                skill_details.append(
                    SkillMatchItem(
                        skill_name=req,
                        is_mandatory=True,
                        is_matched=False,
                        candidate_state=None,
                        weight_credit=0.0
                    )
                )

        # 2. Evaluate Preferred Skills
        for pref in job_preferred:
            norm_pref = self._normalize_skill_key(pref)
            total_pref_points += 0.5

            matched_item = None
            for cand_norm, (cand_state, cand_name) in candidate_skill_map.items():
                if norm_pref == cand_norm or norm_pref in cand_norm or cand_norm in norm_pref:
                    matched_item = (cand_state, cand_name)
                    break

            if matched_item:
                c_state, c_name = matched_item
                credit = state_weight.get(c_state, 0.75)
                earned_pref_points += credit * 0.5
                matched_skills.add(c_name)
                skill_details.append(
                    SkillMatchItem(
                        skill_name=pref,
                        is_mandatory=False,
                        is_matched=True,
                        candidate_state=c_state,
                        weight_credit=credit
                    )
                )
            else:
                missing_preferred.append(pref)
                skill_details.append(
                    SkillMatchItem(
                        skill_name=pref,
                        is_mandatory=False,
                        is_matched=False,
                        candidate_state=None,
                        weight_credit=0.0
                    )
                )

        # Calculate combined skill score
        if total_req_points == 0.0 and total_pref_points == 0.0:
            skill_score = 70.0  # Generic baseline if JD has no tagged skills
        elif total_req_points > 0:
            req_ratio = earned_req_points / total_req_points
            pref_ratio = (earned_pref_points / total_pref_points) if total_pref_points > 0 else 1.0
            # 80% weight on required, 20% on preferred
            skill_score = (req_ratio * 80.0) + (pref_ratio * 20.0)
        else:
            pref_ratio = earned_pref_points / total_pref_points
            skill_score = pref_ratio * 100.0

        return (
            round(min(100.0, max(0.0, skill_score)), 1),
            sorted(list(matched_skills)),
            sorted(missing_mandatory),
            sorted(missing_preferred),
            skill_details
        )

    def evaluate_role_and_seniority(
        self,
        candidate: CandidateProfile,
        job: Job,
        search_profile: Optional[CareerSearchProfile] = None
    ) -> float:
        """Stage 3: Role and seniority semantic overlap score."""
        target_roles: List[str] = []
        if search_profile and search_profile.target_roles:
            target_roles.extend(search_profile.target_roles)
            target_roles.extend(search_profile.alternative_roles)
        if candidate.target_roles:
            target_roles.extend(candidate.target_roles)
        if candidate.current_title:
            target_roles.append(candidate.current_title)

        if not target_roles:
            return 70.0  # Neutral score if no explicit roles configured

        job_title_lower = f"{job.normalized_title} {job.title}".lower()
        job_title_tokens = set(re.findall(r"\b\w+\b", job_title_lower))

        max_overlap_score = 0.0
        for role in target_roles:
            role_tokens = set(re.findall(r"\b\w+\b", role.lower()))
            if not role_tokens:
                continue

            intersection = role_tokens & job_title_tokens
            # If full exact role match
            if role.lower() in job_title_lower or job_title_lower in role.lower():
                max_overlap_score = max(max_overlap_score, 100.0)
                break

            ratio = len(intersection) / len(role_tokens)
            max_overlap_score = max(max_overlap_score, ratio * 90.0)

        return round(min(100.0, max(20.0, max_overlap_score)), 1)

    def evaluate_experience_score(
        self,
        candidate_exp: float,
        job: Job
    ) -> float:
        """Stage 4: Experience fit curve."""
        min_exp = job.min_experience_years or 0.0
        max_exp = job.max_experience_years

        if min_exp == 0.0 and (max_exp is None or max_exp == 0.0):
            return 85.0  # Not specified in JD

        if candidate_exp >= min_exp:
            if max_exp is None or candidate_exp <= max_exp:
                return 100.0  # Perfect fit inside range
            else:
                # Overqualified penalty: slight reduction
                delta = candidate_exp - max_exp
                return max(50.0, round(100.0 - (delta * 8.0), 1))
        else:
            # Underqualified penalty
            deficit = min_exp - candidate_exp
            return max(20.0, round(100.0 - (deficit * 25.0), 1))

    def evaluate_location_score(
        self,
        candidate: CandidateProfile,
        job: Job,
        search_profile: Optional[CareerSearchProfile] = None
    ) -> float:
        """Stage 5: Location and work mode compatibility score."""
        job_loc = (job.location or "").lower()
        if "remote" in job_loc or job.work_mode == WorkModePreference.REMOTE:
            return 100.0

        target_locs = []
        if search_profile and search_profile.locations:
            target_locs.extend([loc.lower() for loc in search_profile.locations])
        elif candidate.location:
            target_locs.append(candidate.location.lower())

        if not target_locs or "flexible" in target_locs or "any" in target_locs:
            return 85.0

        for loc in target_locs:
            if loc in job_loc or job_loc in loc:
                return 100.0

        return 40.0

    def generate_insights(
        self,
        candidate: CandidateProfile,
        job: Job,
        passed_filters: bool,
        rejection_reasons: List[FilterRejectionReason],
        matched_skills: List[str],
        missing_mandatory: List[str],
        missing_preferred: List[str],
        skill_score: float,
        experience_score: float,
        candidate_exp: float
    ) -> Tuple[List[str], List[str], str]:
        """Stage 6: Generates human-readable, explainable match highlights and actionable gaps."""
        highlights: List[str] = []
        concerns: List[str] = []

        # Highlights
        if len(matched_skills) >= 3:
            highlights.append(f"Strong overlap on {len(matched_skills)} core skills ({', '.join(matched_skills[:4])}).")
        elif len(matched_skills) > 0:
            highlights.append(f"Matches key stack requirements: {', '.join(matched_skills)}.")

        if skill_score >= 80.0:
            highlights.append("High skill coverage across required technology stack.")

        if experience_score >= 90.0:
            highlights.append(f"Candidate experience ({candidate_exp} yrs) aligns with job requirements.")

        if job.work_mode == WorkModePreference.REMOTE or "remote" in (job.location or "").lower():
            highlights.append("Fully remote position matching flexible work preferences.")

        # Concerns
        if not passed_filters:
            for reason in rejection_reasons:
                if reason == FilterRejectionReason.LOCATION_MISMATCH:
                    concerns.append(f"Location mismatch: Job is in '{job.location}' which is outside target preferences.")
                elif reason == FilterRejectionReason.EXPERIENCE_TOO_LOW:
                    concerns.append(f"Candidate has {candidate_exp} yrs experience, below job minimum of {job.min_experience_years} yrs.")
                elif reason == FilterRejectionReason.EXPERIENCE_TOO_HIGH:
                    concerns.append(f"Candidate experience ({candidate_exp} yrs) exceeds job target ceiling ({job.max_experience_years} yrs).")
                elif reason == FilterRejectionReason.WORK_MODE_MISMATCH:
                    concerns.append(f"Work mode conflict: Job requires {job.work_mode.value}.")
                elif reason == FilterRejectionReason.EXCLUDED_SKILL_PRESENT:
                    concerns.append("Job includes technologies listed in candidate's excluded skills.")
                elif reason == FilterRejectionReason.SALARY_BELOW_MIN:
                    concerns.append("Job maximum salary is below candidate's specified minimum expectation.")

        if missing_mandatory:
            concerns.append(f"Missing mandatory requirements: {', '.join(missing_mandatory[:4])}.")

        if missing_preferred and len(missing_preferred) >= 2:
            concerns.append(f"Missing preferred bonus skills: {', '.join(missing_preferred[:3])}.")

        # Summary paragraph
        if passed_filters and skill_score >= 75.0:
            summary = f"Strong fit for {job.title} at {job.company}. Matches {len(matched_skills)} required technologies with good seniority alignment."
        elif passed_filters:
            summary = f"Moderate fit for {job.title}. Meets baseline criteria but has skill gaps in {', '.join(missing_mandatory[:2]) if missing_mandatory else 'specialized areas'}."
        else:
            summary = f"Unsuitable match due to hard filter constraints: {', '.join(r.value for r in rejection_reasons)}."

        return highlights, concerns, summary

    def match(
        self,
        candidate: CandidateProfile,
        job: Job,
        search_profile: Optional[CareerSearchProfile] = None,
        strict_filters: bool = True
    ) -> MatchScoreBreakdown:
        """Executes full multi-stage deterministic matching pipeline."""
        candidate_exp = self.calculate_candidate_total_experience(candidate)

        # 1. Hard filters
        passed_filters, rejection_reasons = self.evaluate_hard_filters(
            candidate=candidate,
            job=job,
            search_profile=search_profile,
            candidate_experience_years=candidate_exp
        )

        # 2. Skills
        skill_score, matched_skills, missing_mand, missing_pref, skill_details = self.evaluate_skills(
            candidate_skills=candidate.skills,
            job_required=job.required_skills or [],
            job_preferred=job.preferred_skills or []
        )

        # 3. Role & Seniority
        role_score = self.evaluate_role_and_seniority(candidate, job, search_profile)

        # 4. Experience
        experience_score = self.evaluate_experience_score(candidate_exp, job)

        # 5. Location
        location_score = self.evaluate_location_score(candidate, job, search_profile)

        # 6. Composite Score
        # Weights: Skill 45%, Role 25%, Experience 15%, Location 15%
        raw_score = (
            (skill_score * 0.45)
            + (role_score * 0.25)
            + (experience_score * 0.15)
            + (location_score * 0.15)
        )

        if not passed_filters and strict_filters:
            overall_score = max(0.0, round(raw_score * 0.4, 1))
        else:
            overall_score = round(raw_score, 1)

        # 7. Insights
        highlights, concerns, summary = self.generate_insights(
            candidate=candidate,
            job=job,
            passed_filters=passed_filters,
            rejection_reasons=rejection_reasons,
            matched_skills=matched_skills,
            missing_mandatory=missing_mand,
            missing_preferred=missing_pref,
            skill_score=skill_score,
            experience_score=experience_score,
            candidate_exp=candidate_exp
        )

        return MatchScoreBreakdown(
            overall_score=overall_score,
            skill_score=skill_score,
            role_score=role_score,
            experience_score=experience_score,
            location_score=location_score,
            vector_score=None,
            passed_hard_filters=passed_filters,
            rejection_reasons=rejection_reasons,
            matched_skills=matched_skills,
            missing_mandatory_skills=missing_mand,
            missing_preferred_skills=missing_pref,
            skill_details=skill_details,
            highlights=highlights,
            concerns=concerns,
            reasoning_summary=summary
        )


matching_engine = MatchingEngine()
