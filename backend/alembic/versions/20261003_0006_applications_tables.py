"""Create job_applications table

Revision ID: 20261003_0006
Revises: 20261002_0005
Create Date: 2026-10-03 11:48:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20261003_0006'
down_revision: Union[str, None] = '20261002_0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'job_applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),

        # Foreign keys
        sa.Column(
            'candidate_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('candidate_profiles.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'job_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('jobs.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column(
            'resume_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('tailored_resumes.id', ondelete='SET NULL'),
            nullable=True,
        ),

        # Lifecycle
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DISCOVERED'),

        # Application details
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('external_job_url', sa.String(length=2048), nullable=True),
        sa.Column('external_application_id', sa.String(length=255), nullable=True),
        sa.Column('cover_letter', sa.Text(), nullable=True),

        # Form mapping (APP-001)
        sa.Column('detected_form_fields', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('mapped_field_values', sa.JSON(), nullable=False, server_default='{}'),

        # Automation metadata (APP-002)
        sa.Column('automation_level', sa.String(length=50), nullable=True),
        sa.Column('handoff_count', sa.Integer(), nullable=False, server_default='0'),

        # Notes & audit
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('transition_history', sa.JSON(), nullable=False, server_default='[]'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index('ix_job_applications_candidate_id', 'job_applications', ['candidate_id'])
    op.create_index('ix_job_applications_job_id', 'job_applications', ['job_id'])
    op.create_index('ix_job_applications_status', 'job_applications', ['status'])
    op.create_index(
        'ix_job_applications_candidate_status',
        'job_applications',
        ['candidate_id', 'status'],
    )


def downgrade() -> None:
    op.drop_index('ix_job_applications_candidate_status', table_name='job_applications')
    op.drop_index('ix_job_applications_status', table_name='job_applications')
    op.drop_index('ix_job_applications_job_id', table_name='job_applications')
    op.drop_index('ix_job_applications_candidate_id', table_name='job_applications')
    op.drop_table('job_applications')
