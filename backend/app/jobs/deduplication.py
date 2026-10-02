"""Multi-signal job deduplication engine."""

import hashlib
import re
from typing import Optional
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.models import Job
from app.jobs.enums import JobSourceType


def generate_content_hash(company: str, normalized_title: str, description_clean: str) -> str:
    """Generates a deterministic SHA-256 content signature for exact text deduplication."""
    norm_comp = re.sub(r"[^\w]", "", company.lower())
    norm_titl = re.sub(r"[^\w]", "", normalized_title.lower())
    # Use first 1000 chars of description to protect against dynamic footers / tracking text
    norm_desc = re.sub(r"[^\w]", "", description_clean[:1000].lower())
    payload = f"{norm_comp}|{norm_titl}|{norm_desc}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class DeduplicationEngine:
    """Finds existing matching jobs across multiple platform signals."""

    @staticmethod
    async def find_existing_job(
        db: AsyncSession,
        source: JobSourceType,
        source_job_id: Optional[str],
        canonical_url: Optional[str],
        content_hash: str,
        company: str,
        normalized_title: str,
        location: str
    ) -> Optional[Job]:
        """Runs multi-signal checks to find any duplicate job in the database."""
        
        # Signal 1: Exact Content Hash Match
        query = select(Job).where(Job.content_hash == content_hash)
        res = await db.execute(query)
        job = res.scalar_one_or_none()
        if job:
            return job

        # Signal 2: Platform + Source Job ID Match
        if source_job_id:
            query = select(Job).where(
                Job.source == source,
                Job.source_job_id == source_job_id
            )
            res = await db.execute(query)
            job = res.scalar_one_or_none()
            if job:
                return job

        # Signal 3: Canonical URL Match
        if canonical_url and len(canonical_url) > 10:
            query = select(Job).where(Job.canonical_url == canonical_url)
            res = await db.execute(query)
            job = res.scalar_one_or_none()
            if job:
                return job

        # Signal 4: Company + Normalized Title + Location Match
        query = select(Job).where(
            Job.company.ilike(company.strip()),
            Job.normalized_title.ilike(normalized_title.strip()),
            Job.location.ilike(location.strip())
        )
        res = await db.execute(query)
        job = res.scalar_one_or_none()
        if job:
            return job

        return None
