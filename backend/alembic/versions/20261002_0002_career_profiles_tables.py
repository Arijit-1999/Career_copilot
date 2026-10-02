"""Create career search profiles table

Revision ID: 20261002_0002
Revises: 20261002_0001
Create Date: 2026-10-02 22:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20261002_0002'
down_revision: Union[str, None] = '20261002_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'career_search_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('target_roles', sa.JSON(), nullable=False),
        sa.Column('alternative_roles', sa.JSON(), nullable=False),
        sa.Column('required_skills', sa.JSON(), nullable=False),
        sa.Column('preferred_skills', sa.JSON(), nullable=False),
        sa.Column('excluded_skills', sa.JSON(), nullable=False),
        sa.Column('locations', sa.JSON(), nullable=False),
        sa.Column('work_modes', sa.JSON(), nullable=False),
        sa.Column('min_experience_years', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('max_experience_years', sa.Float(), nullable=True),
        sa.Column('min_salary', sa.Float(), nullable=True),
        sa.Column('target_salary', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('intent_query', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_career_search_profiles_candidate_id', 'career_search_profiles', ['candidate_id'])


def downgrade() -> None:
    op.drop_table('career_search_profiles')
