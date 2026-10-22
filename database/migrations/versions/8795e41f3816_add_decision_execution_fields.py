"""add_decision_execution_fields

Revision ID: 8795e41f3816
Revises: 872f0be7f6dd
Create Date: 2026-10-22 11:05:18.616051

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8795e41f3816'
down_revision: Union[str, None] = '872f0be7f6dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns to decisions table
    op.add_column('decisions', sa.Column('shipment_id', sa.String(length=50), nullable=True))
    op.add_column('decisions', sa.Column('optimization_run_id', sa.String(length=50), nullable=True))
    op.add_column('decisions', sa.Column('option_id', sa.String(length=10), nullable=True))
    op.add_column('decisions', sa.Column('strategy', sa.String(length=50), nullable=True))
    op.add_column('decisions', sa.Column('estimated_total_cost', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('decisions', sa.Column('currency', sa.String(length=10), server_default='USD', nullable=True))
    op.add_column('decisions', sa.Column('estimated_delivery_days', sa.Numeric(precision=6, scale=2), nullable=True))
    op.add_column('decisions', sa.Column('delay_probability', sa.Numeric(precision=5, scale=4), nullable=True))
    op.add_column('decisions', sa.Column('constraint_validation_snapshot', sa.JSON(), nullable=True))
    op.add_column('decisions', sa.Column('idempotency_key', sa.String(length=100), nullable=True))
    op.add_column('decisions', sa.Column('external_action_status', sa.String(length=50), server_default='NOT_EXECUTED', nullable=True))
    op.add_column('decisions', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))

    # 2. Create indexes
    op.create_index(op.f('ix_decisions_shipment_id'), 'decisions', ['shipment_id'], unique=False)
    op.create_index(op.f('ix_decisions_optimization_run_id'), 'decisions', ['optimization_run_id'], unique=False)
    op.create_index(op.f('ix_decisions_idempotency_key'), 'decisions', ['idempotency_key'], unique=True)

    # 3. Widen status check constraint
    op.drop_constraint('ck_decisions_status', 'decisions', type_='check')
    op.create_check_constraint(
        'ck_decisions_status',
        'decisions',
        "status IN ('Pending', 'Approved', 'Rejected', 'Executed', 'Cancelled', 'RECORDED', 'PENDING_CONFIRMATION', 'FAILED')",
    )


def downgrade() -> None:
    # 1. Restore original status check constraint
    op.drop_constraint('ck_decisions_status', 'decisions', type_='check')
    op.create_check_constraint(
        'ck_decisions_status',
        'decisions',
        "status IN ('Pending', 'Approved', 'Rejected', 'Executed', 'Cancelled')",
    )

    # 2. Drop indexes
    op.drop_index(op.f('ix_decisions_idempotency_key'), table_name='decisions')
    op.drop_index(op.f('ix_decisions_optimization_run_id'), table_name='decisions')
    op.drop_index(op.f('ix_decisions_shipment_id'), table_name='decisions')

    # 3. Drop columns
    op.drop_column('decisions', 'updated_at')
    op.drop_column('decisions', 'external_action_status')
    op.drop_column('decisions', 'idempotency_key')
    op.drop_column('decisions', 'constraint_validation_snapshot')
    op.drop_column('decisions', 'delay_probability')
    op.drop_column('decisions', 'estimated_delivery_days')
    op.drop_column('decisions', 'currency')
    op.drop_column('decisions', 'estimated_total_cost')
    op.drop_column('decisions', 'strategy')
    op.drop_column('decisions', 'option_id')
    op.drop_column('decisions', 'optimization_run_id')
    op.drop_column('decisions', 'shipment_id')
