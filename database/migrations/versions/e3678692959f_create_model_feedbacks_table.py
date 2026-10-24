"""create_model_feedbacks_table

Revision ID: e3678692959f
Revises: 6c26ac4fad37
Create Date: 2026-10-24 10:45:39.108714

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3678692959f'
down_revision: Union[str, None] = '6c26ac4fad37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'model_feedbacks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('feedback_id', sa.String(length=50), nullable=False),
        sa.Column('prediction_id', sa.String(length=50), nullable=False),
        sa.Column('shipment_id', sa.String(length=50), nullable=False),
        sa.Column('decision_id', sa.String(length=50), nullable=True),
        sa.Column('predicted_delay', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('actual_delay', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('prediction_error', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('absolute_error', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('prediction_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('outcome_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('feedback_status', sa.String(length=50), server_default='PENDING_OUTCOME', nullable=False),
        sa.Column('exclusion_reason', sa.String(length=255), nullable=True),
        sa.Column('dataset_version', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('feedback_id', name='uq_model_feedbacks_feedback_id'),
        sa.UniqueConstraint('prediction_id', name='uq_model_feedbacks_prediction_id'),
        sa.CheckConstraint(
            "feedback_status IN ('ELIGIBLE', 'PENDING_OUTCOME', 'EXCLUDED', 'UNDER_REVIEW')",
            name='ck_model_feedbacks_status'
        ),
        sa.CheckConstraint(
            "absolute_error IS NULL OR absolute_error >= 0",
            name='ck_model_feedbacks_absolute_error'
        ),
        sa.ForeignKeyConstraint(
            ['shipment_id'], ['shipments.shipment_id'],
            name='fk_model_feedbacks_shipment_id',
            ondelete='SET NULL'
        ),
    )
    op.create_index('ix_model_feedbacks_feedback_id', 'model_feedbacks', ['feedback_id'])
    op.create_index('ix_model_feedbacks_prediction_id', 'model_feedbacks', ['prediction_id'])
    op.create_index('ix_model_feedbacks_shipment_id', 'model_feedbacks', ['shipment_id'])
    op.create_index('ix_model_feedbacks_decision_id', 'model_feedbacks', ['decision_id'])
    op.create_index('ix_model_feedbacks_model_version', 'model_feedbacks', ['model_version'])
    op.create_index('ix_model_feedbacks_feedback_status', 'model_feedbacks', ['feedback_status'])
    op.create_index('ix_model_feedbacks_dataset_version', 'model_feedbacks', ['dataset_version'])


def downgrade() -> None:
    op.drop_index('ix_model_feedbacks_dataset_version', table_name='model_feedbacks')
    op.drop_index('ix_model_feedbacks_feedback_status', table_name='model_feedbacks')
    op.drop_index('ix_model_feedbacks_model_version', table_name='model_feedbacks')
    op.drop_index('ix_model_feedbacks_decision_id', table_name='model_feedbacks')
    op.drop_index('ix_model_feedbacks_shipment_id', table_name='model_feedbacks')
    op.drop_index('ix_model_feedbacks_prediction_id', table_name='model_feedbacks')
    op.drop_index('ix_model_feedbacks_feedback_id', table_name='model_feedbacks')
    op.drop_table('model_feedbacks')
