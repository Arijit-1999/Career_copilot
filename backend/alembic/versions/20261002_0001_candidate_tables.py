"""Create candidate profile, skills, and resume fact bank tables

Revision ID: 20261002_0001
Revises: 
Create Date: 2026-10-02 22:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20261002_0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure vector extension is present
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. candidate_profiles
    op.create_table(
        'candidate_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('current_title', sa.String(length=255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('target_roles', sa.JSON(), nullable=False),
        sa.Column('work_mode', sa.String(length=50), nullable=False, server_default='FLEXIBLE'),
        sa.Column('min_salary', sa.Float(), nullable=True),
        sa.Column('target_salary', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_candidate_profiles_email', 'candidate_profiles', ['email'])

    # 2. skills
    op.create_table(
        'skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=150), nullable=False, unique=True),
        sa.Column('canonical_name', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_skills_canonical_name', 'skills', ['canonical_name'])

    # 3. candidate_skills
    op.create_table(
        'candidate_skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='CLAIMED'),
        sa.Column('years_experience', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('confidence_level', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('evidence_notes', sa.Text(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('candidate_id', 'skill_id', name='uq_candidate_skill')
    )
    op.create_index('ix_candidate_skills_candidate_id', 'candidate_skills', ['candidate_id'])
    op.create_index('ix_candidate_skills_state', 'candidate_skills', ['state'])

    # 4. resume_facts
    op.create_table(
        'resume_facts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('fact_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=False),
        sa.Column('source_reference', sa.String(length=255), nullable=True),
        sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='UNVERIFIED'),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_resume_facts_candidate_id', 'resume_facts', ['candidate_id'])
    op.create_index('ix_resume_facts_fact_type', 'resume_facts', ['fact_type'])

    # 5. candidate_experiences
    op.create_table(
        'candidate_experiences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )

    # 6. candidate_projects
    op.create_table(
        'candidate_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tech_stack', sa.JSON(), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('repo_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('candidate_projects')
    op.drop_table('candidate_experiences')
    op.drop_table('resume_facts')
    op.drop_table('candidate_skills')
    op.drop_table('skills')
    op.drop_table('candidate_profiles')
