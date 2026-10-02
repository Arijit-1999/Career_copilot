"""Create jobs table

Revision ID: 20261002_0003
Revises: 20261002_0002
Create Date: 2026-10-02 23:18:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20261002_0003'
down_revision: Union[str, None] = '20261002_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='MANUAL'),
        sa.Column('source_job_id', sa.String(length=255), nullable=True),
        sa.Column('application_url', sa.String(length=1000), nullable=True),
        sa.Column('canonical_url', sa.String(length=1000), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('normalized_title', sa.String(length=255), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=False, server_default='Remote'),
        sa.Column('work_mode', sa.String(length=50), nullable=False, server_default='FLEXIBLE'),
        sa.Column('employment_type', sa.String(length=50), nullable=False, server_default='Full-time'),
        sa.Column('salary_min', sa.Float(), nullable=True),
        sa.Column('salary_max', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('salary_raw', sa.String(length=255), nullable=True),
        sa.Column('min_experience_years', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('max_experience_years', sa.Float(), nullable=True),
        sa.Column('description_raw', sa.Text(), nullable=False),
        sa.Column('description_clean', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('required_skills', sa.JSON(), nullable=False),
        sa.Column('preferred_skills', sa.JSON(), nullable=False),
        sa.Column('extracted_tags', sa.JSON(), nullable=False),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('freshness', sa.String(length=50), nullable=False, server_default='VERY_FRESH'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DISCOVERED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_jobs_source_source_id', 'jobs', ['source', 'source_job_id'])
    op.create_index('ix_jobs_content_hash', 'jobs', ['content_hash'])
    op.create_index('ix_jobs_canonical_url', 'jobs', ['canonical_url'])
    op.create_index('ix_jobs_company_title', 'jobs', ['company', 'normalized_title'])
    op.create_index('ix_jobs_title', 'jobs', ['title'])
    op.create_index('ix_jobs_company', 'jobs', ['company'])


def downgrade() -> None:
    op.drop_table('jobs')
