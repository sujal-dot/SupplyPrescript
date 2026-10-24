"""create_retraining_jobs_table

Revision ID: a794b281f3e1
Revises: e3678692959f
Create Date: 2026-10-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a794b281f3e1'
down_revision: Union[str, None] = 'e3678692959f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'retraining_jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.String(length=64), nullable=False),
        sa.Column('trigger_reason', sa.String(length=255), nullable=False),
        sa.Column('triggered_by', sa.String(length=100), server_default='system_pipeline', nullable=False),
        sa.Column('model_name', sa.String(length=100), server_default='supplyprescript_delay_engine', nullable=False),
        sa.Column('parent_model_version', sa.String(length=32), nullable=False),
        sa.Column('candidate_model_version', sa.String(length=32), nullable=True),
        sa.Column('dataset_version', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='QUEUED', nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('baseline_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('candidate_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('acceptance_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id', name='uq_retraining_jobs_job_id'),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'EVALUATING', 'REGISTERED', 'PROMOTED', 'REJECTED', 'FAILED', 'INSUFFICIENT_DATA', 'CANCELLED')",
            name='ck_retraining_jobs_status'
        ),
    )
    op.create_index('ix_retraining_jobs_job_id', 'retraining_jobs', ['job_id'])
    op.create_index('ix_retraining_jobs_status', 'retraining_jobs', ['status'])
    op.create_index('ix_retraining_jobs_candidate_model_version', 'retraining_jobs', ['candidate_model_version'])
    op.create_index('ix_retraining_jobs_dataset_version', 'retraining_jobs', ['dataset_version'])


def downgrade() -> None:
    op.drop_index('ix_retraining_jobs_dataset_version', table_name='retraining_jobs')
    op.drop_index('ix_retraining_jobs_candidate_model_version', table_name='retraining_jobs')
    op.drop_index('ix_retraining_jobs_status', table_name='retraining_jobs')
    op.drop_index('ix_retraining_jobs_job_id', table_name='retraining_jobs')
    op.drop_table('retraining_jobs')
