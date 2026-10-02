"""Create job_matches table

Revision ID: 20261002_0004
Revises: 20261002_0003
Create Date: 2026-10-02 23:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20261002_0004'
down_revision: Union[str, None] = '20261002_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'job_matches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('search_profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('career_search_profiles.id', ondelete='SET NULL'), nullable=True),
        
        sa.Column('overall_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('skill_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('role_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('experience_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('location_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('vector_score', sa.Float(), nullable=True),
        
        sa.Column('status', sa.String(length=50), nullable=False, server_default='MODERATE_MATCH'),
        sa.Column('passed_hard_filters', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('filter_rejection_reasons', sa.JSON(), nullable=False, server_default='[]'),
        
        sa.Column('matched_skills', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('missing_mandatory_skills', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('missing_preferred_skills', sa.JSON(), nullable=False, server_default='[]'),
        
        sa.Column('highlights', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('concerns', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('reasoning_summary', sa.Text(), nullable=True),
        
        sa.Column('is_dismissed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_starred', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_applied', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('candidate_id', 'job_id', name='uq_candidate_job_match')
    )
    op.create_index('ix_job_matches_candidate_id', 'job_matches', ['candidate_id'])
    op.create_index('ix_job_matches_job_id', 'job_matches', ['job_id'])
    op.create_index('ix_job_matches_search_profile_id', 'job_matches', ['search_profile_id'])
    op.create_index('ix_job_matches_candidate_score', 'job_matches', ['candidate_id', 'overall_score'])
    op.create_index('ix_job_matches_status', 'job_matches', ['status'])


def downgrade() -> None:
    op.drop_index('ix_job_matches_status', table_name='job_matches')
    op.drop_index('ix_job_matches_candidate_score', table_name='job_matches')
    op.drop_index('ix_job_matches_search_profile_id', table_name='job_matches')
    op.drop_index('ix_job_matches_job_id', table_name='job_matches')
    op.drop_index('ix_job_matches_candidate_id', table_name='job_matches')
    op.drop_table('job_matches')
