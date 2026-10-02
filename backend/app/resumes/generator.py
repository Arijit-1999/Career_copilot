"""Minimal-change, ATS-compliant Markdown Resume Generator."""

from typing import List, Optional
from app.resumes.schemas import (
    ResumeStructuredContent,
    ResumeSkillGroup,
    ResumeExperienceItem,
    ResumeProjectItem
)


class ResumeGenerator:
    """Renders structured resume content into standard ATS-friendly Markdown."""

    def render_markdown(self, content: ResumeStructuredContent) -> str:
        """Generates clean Markdown representation of the structured resume."""
        lines: List[str] = []

        # 1. Header
        header = content.header
        lines.append(f"# {header.full_name}")
        if header.title:
            lines.append(f"**{header.title}**")

        contact_parts = [header.email]
        if header.phone:
            contact_parts.append(header.phone)
        if header.location:
            contact_parts.append(header.location)
        lines.append(" • ".join(contact_parts))
        lines.append("\n---\n")

        # 2. Summary
        if content.summary:
            lines.append("## Professional Summary")
            lines.append(content.summary.strip())
            lines.append("")

        # 3. Core Competencies / Technical Skills
        if content.skill_groups:
            lines.append("## Core Technical Competencies")
            for group in content.skill_groups:
                if group.skills:
                    skills_joined = ", ".join(group.skills)
                    lines.append(f"- **{group.category_name}**: {skills_joined}")
            lines.append("")

        # 4. Professional Experience
        if content.experiences:
            lines.append("## Professional Experience")
            for exp in content.experiences:
                loc_str = f" | {exp.location}" if exp.location else ""
                lines.append(f"### {exp.title} — **{exp.company}**{loc_str}")
                lines.append(f"*{exp.start_date} – {exp.end_date}*")
                for bullet in exp.bullets:
                    lines.append(f"- {bullet}")
                lines.append("")

        # 5. Key Projects
        if content.projects:
            lines.append("## Key Engineering Projects")
            for proj in content.projects:
                role_str = f" (*{proj.role}*)" if proj.role else ""
                url_str = f" — [{proj.url}]({proj.url})" if proj.url else ""
                lines.append(f"### {proj.name}{role_str}{url_str}")
                if proj.description:
                    lines.append(proj.description)
                if proj.tech_stack:
                    lines.append(f"- **Technologies**: {', '.join(proj.tech_stack)}")
                lines.append("")

        # 6. Education
        if content.education:
            lines.append("## Education")
            for edu in content.education:
                lines.append(f"- {edu}")
            lines.append("")

        return "\n".join(lines)


resume_generator = ResumeGenerator()
