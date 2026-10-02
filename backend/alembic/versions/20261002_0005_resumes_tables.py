"""Create tailored_resumes table

Revision ID: 20261002_0005
Revises: 20261002_0004
Create Date: 2026-10-03 00:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20261002_0005'
down_revision: Union[str, None] = '20261002_0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tailored_resumes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='SET NULL'), nullable=True),
        
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('target_role', sa.String(length=255), nullable=True),
        
        sa.Column('raw_markdown', sa.Text(), nullable=False),
        sa.Column('structured_content', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('targeted_skills', sa.JSON(), nullable=False, server_default='[]'),
        
        sa.Column('is_master', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='VERIFIED_TAILORED'),
        sa.Column('truth_score', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('validation_report', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('user_notes', sa.Text(), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )
    op.create_index('ix_tailored_resumes_candidate_id', 'tailored_resumes', ['candidate_id'])
    op.create_index('ix_tailored_resumes_candidate_master', 'tailored_resumes', ['candidate_id', 'is_master'])
    op.create_index('ix_tailored_resumes_job_id', 'tailored_resumes', ['job_id'])
    op.create_index('ix_tailored_resumes_status', 'tailored_resumes', ['status'])


def downgrade() -> None:
    op.drop_index('ix_tailored_resumes_status', table_name='tailored_resumes')
    op.drop_index('ix_tailored_resumes_job_id', table_name='tailored_resumes')
    op.drop_index('ix_tailored_resumes_candidate_master', table_name='tailored_resumes')
    op.drop_index('ix_tailored_resumes_candidate_id', table_name='tailored_resumes')
    op.drop_table('tailored_resumes')
