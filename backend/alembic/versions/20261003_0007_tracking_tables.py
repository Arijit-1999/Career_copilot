"""Create tracking and analytics tables (timeline, interviews, outcomes)

Revision ID: 20261003_0007
Revises: 20261003_0006
Create Date: 2026-10-03 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20261003_0007'
down_revision: Union[str, None] = '20261003_0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Timeline Events Table
    op.create_table(
        'application_timeline_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'application_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('job_applications.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('from_status', sa.String(50), nullable=True),
        sa.Column('to_status', sa.String(50), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('extra_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_timeline_app_id', 'application_timeline_events', ['application_id'])
    op.create_index('ix_timeline_event_type', 'application_timeline_events', ['event_type'])
    op.create_index('ix_timeline_event_timestamp', 'application_timeline_events', ['event_timestamp'])

    # 2. Interviews Table
    op.create_table(
        'application_interviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'application_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('job_applications.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('round_type', sa.String(50), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('format', sa.String(50), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('interviewer_names', sa.String(500), nullable=True),
        sa.Column('interviewer_titles', sa.String(500), nullable=True),
        sa.Column('meeting_link', sa.String(2048), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('preparation_notes', sa.Text(), nullable=True),
        sa.Column('questions_asked', sa.Text(), nullable=True),
        sa.Column('feedback_received', sa.Text(), nullable=True),
        sa.Column('outcome', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_interviews_app_id', 'application_interviews', ['application_id'])
    op.create_index('ix_interviews_scheduled_at', 'application_interviews', ['scheduled_at'])
    op.create_index('ix_interviews_outcome', 'application_interviews', ['outcome'])

    # 3. Outcomes Table
    op.create_table(
        'application_outcomes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'application_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('job_applications.id', ondelete='CASCADE'),
            nullable=False,
            unique=True,
        ),
        sa.Column('final_status', sa.String(50), nullable=False),
        sa.Column('rejection_category', sa.String(50), nullable=True),
        sa.Column('rejection_feedback', sa.Text(), nullable=True),
        sa.Column('offer_outcome', sa.String(50), nullable=True),
        sa.Column('offer_salary_amount', sa.Float(), nullable=True),
        sa.Column('offer_salary_currency', sa.String(10), nullable=True),
        sa.Column('offer_equity', sa.String(255), nullable=True),
        sa.Column('offer_bonus', sa.String(255), nullable=True),
        sa.Column('offer_deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lessons_learned', sa.Text(), nullable=True),
        sa.Column('response_time_days', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_outcomes_app_id', 'application_outcomes', ['application_id'], unique=True)
    op.create_index('ix_outcomes_final_status', 'application_outcomes', ['final_status'])
    op.create_index('ix_outcomes_rejection_cat', 'application_outcomes', ['rejection_category'])


def downgrade() -> None:
    op.drop_table('application_outcomes')
    op.drop_table('application_interviews')
    op.drop_table('application_timeline_events')
