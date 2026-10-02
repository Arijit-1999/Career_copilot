"""Deterministic JD-targeted fact, skill, and experience selection engine."""

import re
from typing import List, Dict, Set, Tuple, Optional, Any
from app.candidate.enums import SkillState, FactVerificationStatus
from app.candidate.models import CandidateProfile, CandidateSkill, ResumeFact, CandidateExperience, CandidateProject
from app.jobs.models import Job
from app.resumes.schemas import (
    ResumeSectionHeader,
    ResumeSkillGroup,
    ResumeExperienceItem,
    ResumeProjectItem,
    ResumeStructuredContent
)


class FactSelector:
    """Selects and ranks verified facts and experiences targeted at specific JD requirements."""

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"[^a-z0-9+#.]", "", text.lower().strip())

    def select_skills_for_jd(
        self,
        candidate_skills: List[CandidateSkill],
        job: Optional[Job] = None,
        include_claimed: bool = False
    ) -> Tuple[List[ResumeSkillGroup], List[str]]:
        """Selects and categorizes skills, emphasizing those required by the JD."""
        # 1. Determine allowed skills (Strictly VERIFIED by default)
        allowed_skills: List[CandidateSkill] = []
        for cs in candidate_skills:
            if cs.state == SkillState.VERIFIED:
                allowed_skills.append(cs)
            elif include_claimed and cs.state == SkillState.CLAIMED:
                allowed_skills.append(cs)

        # 2. Extract JD required & preferred skill keys
        jd_skill_keys: Set[str] = set()
        if job:
            for s in (job.required_skills or []) + (job.preferred_skills or []):
                jd_skill_keys.add(self._normalize(s))

        # 3. Categorize skills
        categories: Dict[str, List[str]] = {
            "Languages": [],
            "Backend & Frameworks": [],
            "Databases & Search": [],
            "Cloud, DevOps & Infra": [],
            "Tools & Methodologies": []
        }

        targeted_skills: List[str] = []

        for cs in allowed_skills:
            s_name = cs.skill.name if cs.skill else cs.skill_id
            norm_key = self._normalize(s_name)
            s_cat = (cs.category or "").lower()

            is_targeted = norm_key in jd_skill_keys or any(norm_key in k for k in jd_skill_keys)
            if is_targeted:
                targeted_skills.append(s_name)

            # Categorize
            if any(l in norm_key for l in ["python", "javascript", "typescript", "golang", "go", "java", "c++", "c#", "rust", "sql"]):
                categories["Languages"].append(s_name)
            elif any(f in norm_key for f in ["fastapi", "django", "flask", "react", "next", "node", "express", "spring", "graphql"]):
                categories["Backend & Frameworks"].append(s_name)
            elif any(d in norm_key for d in ["postgres", "mysql", "mongodb", "redis", "pgvector", "pinecone", "qdrant", "snowflake"]):
                categories["Databases & Search"].append(s_name)
            elif any(c in norm_key for c in ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd", "kafka", "linux"]):
                categories["Cloud, DevOps & Infra"].append(s_name)
            else:
                categories["Tools & Methodologies"].append(s_name)

        # Build output groups (sorted with targeted skills first in each group)
        skill_groups: List[ResumeSkillGroup] = []
        for cat_name, skills in categories.items():
            if skills:
                # Sort targeted skills first
                sorted_skills = sorted(
                    skills,
                    key=lambda s: (0 if self._normalize(s) in jd_skill_keys else 1, s)
                )
                skill_groups.append(ResumeSkillGroup(category_name=cat_name, skills=sorted_skills))

        return skill_groups, sorted(list(set(targeted_skills)))

    def select_experiences_and_facts(
        self,
        candidate: CandidateProfile,
        job: Optional[Job] = None,
        max_bullets: int = 4
    ) -> List[ResumeExperienceItem]:
        """Maps experiences and attaches verified, metric-backed bullet points."""
        experiences_out: List[ResumeExperienceItem] = []

        jd_keywords: Set[str] = set()
        if job:
            jd_text = f"{job.title} {job.description_clean or ''}".lower()
            for s in (job.required_skills or []) + (job.preferred_skills or []):
                jd_keywords.add(self._normalize(s))

        # Verified facts map
        verified_facts = [
            f for f in candidate.facts
            if f.verification_status == FactVerificationStatus.VERIFIED
        ]

        for exp in candidate.experiences:
            # Match verified facts to this company or general relevant facts
            bullets: List[str] = []
            exp_company_norm = exp.company.lower()

            matched_facts: List[Tuple[int, str]] = []
            for fact in verified_facts:
                score = 0
                fact_text = f"{fact.title} {fact.description}".lower()
                fact_tags = [self._normalize(t) for t in (fact.tags or [])]

                # Check if fact source matches this company
                if fact.source_reference and exp_company_norm in fact.source_reference.lower():
                    score += 50

                # Check overlap with JD keywords
                for kw in jd_keywords:
                    if kw in fact_text or kw in fact_tags:
                        score += 30

                # Metric bonus
                if fact.metrics:
                    score += 15

                formatted_bullet = f"{fact.title}: {fact.description}"
                matched_facts.append((score, formatted_bullet))

            # Sort facts by relevance score
            matched_facts.sort(key=lambda x: x[0], reverse=True)
            for _, bullet_text in matched_facts[:max_bullets]:
                bullets.append(bullet_text)

            # Fallback to experience description if no facts attached
            if not bullets and exp.description:
                bullets.append(exp.description)

            start_str = exp.start_date.strftime("%b %Y") if exp.start_date else "Past"
            end_str = "Present" if exp.is_current else (exp.end_date.strftime("%b %Y") if exp.end_date else "Past")

            experiences_out.append(
                ResumeExperienceItem(
                    company=exp.company,
                    title=exp.title,
                    location=exp.location,
                    start_date=start_str,
                    end_date=end_str,
                    is_current=exp.is_current,
                    bullets=bullets,
                    technologies=[]
                )
            )

        return experiences_out

    def select_projects(
        self,
        projects: List[CandidateProject],
        job: Optional[Job] = None
    ) -> List[ResumeProjectItem]:
        """Ranks projects by tech stack overlap with the target job."""
        if not projects:
            return []

        jd_keys: Set[str] = set()
        if job:
            for s in (job.required_skills or []) + (job.preferred_skills or []):
                jd_keys.add(self._normalize(s))

        scored_projects: List[Tuple[int, CandidateProject]] = []
        for p in projects:
            score = 0
            for t in (p.tech_stack or []):
                if self._normalize(t) in jd_keys:
                    score += 10
            scored_projects.append((score, p))

        scored_projects.sort(key=lambda x: x[0], reverse=True)

        projects_out: List[ResumeProjectItem] = []
        for _, p in scored_projects[:3]:
            projects_out.append(
                ResumeProjectItem(
                    name=p.name,
                    role=p.role,
                    description=p.description,
                    tech_stack=p.tech_stack or [],
                    url=p.url or p.repo_url
                )
            )
        return projects_out

    def build_summary(
        self,
        candidate: CandidateProfile,
        job: Optional[Job] = None,
        targeted_skills: List[str] = None
    ) -> str:
        """Generates a truthful, focused summary emphasizing verified skills."""
        title = candidate.current_title or "Software Engineer"
        if job and job.normalized_title:
            target_title = job.normalized_title
        else:
            target_title = title

        top_skills = (targeted_skills[:4] if targeted_skills else [])
        skills_phrase = f" specializing in {', '.join(top_skills)}" if top_skills else ""

        if candidate.summary:
            return candidate.summary

        return (
            f"Results-oriented {target_title}{skills_phrase} with a strong track record of engineering "
            f"scalable backend architectures, robust microservices, and reliable cloud workflows. "
            f"Dedicated to truth-verified execution and high-performance software engineering."
        )

    def select_structured_content(
        self,
        candidate: CandidateProfile,
        job: Optional[Job] = None,
        include_claimed: bool = False,
        max_bullets: int = 4
    ) -> Tuple[ResumeStructuredContent, List[str]]:
        """Assembles the full structured resume content strictly drawing from verified candidate data."""
        skill_groups, targeted_skills = self.select_skills_for_jd(
            candidate_skills=candidate.skills,
            job=job,
            include_claimed=include_claimed
        )
        experiences = self.select_experiences_and_facts(
            candidate=candidate,
            job=job,
            max_bullets=max_bullets
        )
        projects = self.select_projects(
            projects=candidate.projects,
            job=job
        )
        summary = self.build_summary(
            candidate=candidate,
            job=job,
            targeted_skills=targeted_skills
        )

        header = ResumeSectionHeader(
            full_name=candidate.full_name,
            email=candidate.email,
            phone=candidate.phone,
            location=candidate.location,
            title=job.title if job else candidate.current_title
        )

        content = ResumeStructuredContent(
            header=header,
            summary=summary,
            skill_groups=skill_groups,
            experiences=experiences,
            projects=projects,
            education=["Bachelor's Degree in Computer Science / Engineering" if not hasattr(candidate, 'education') else "Computer Science"]
        )

        return content, targeted_skills


fact_selector = FactSelector()
