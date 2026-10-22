"""add_outcome_tracking_fields

Revision ID: 6c26ac4fad37
Revises: 21e279b9475a
Create Date: 2026-10-22 11:47:17.350190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c26ac4fad37'
down_revision: Union[str, None] = '21e279b9475a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add Day 19 Closed-Loop Outcome Tracking fields
    op.add_column('outcomes', sa.Column('shipment_id', sa.String(length=50), nullable=True))
    op.add_column('outcomes', sa.Column('decision_business_id', sa.String(length=64), nullable=True))
    op.add_column('outcomes', sa.Column('currency', sa.String(length=10), server_default='USD', nullable=True))
    op.add_column('outcomes', sa.Column('actual_delay', sa.Numeric(precision=6, scale=2), nullable=True))
    op.add_column('outcomes', sa.Column('baseline_delivery_date', sa.Date(), nullable=True))
    op.add_column('outcomes', sa.Column('actual_supplier', sa.String(length=100), nullable=True))
    op.add_column('outcomes', sa.Column('actual_quantity', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('outcomes', sa.Column('source', sa.String(length=50), server_default='manual_entry', nullable=True))
    op.add_column('outcomes', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('outcomes', sa.Column('recorded_by', sa.String(length=100), nullable=True))
    op.add_column('outcomes', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))

    # 2. Backfill existing rows with decision data
    op.execute("""
        UPDATE outcomes
        SET decision_business_id = d.decision_id,
            shipment_id = d.shipment_id,
            actual_delay = outcomes.actual_delay_days,
            notes = outcomes.outcome_notes,
            currency = COALESCE(d.currency, 'USD'),
            source = 'legacy_migration'
        FROM decisions d
        WHERE outcomes.decision_id = d.id
    """)

    # 3. Foreign Key to shipments
    op.create_foreign_key(
        'fk_outcomes_shipment_id',
        'outcomes', 'shipments',
        ['shipment_id'], ['shipment_id'],
        ondelete='SET NULL'
    )

    # 4. Indexes
    op.create_index('ix_outcomes_shipment_id', 'outcomes', ['shipment_id'])
    op.create_index('ix_outcomes_decision_business_id', 'outcomes', ['decision_business_id'])
    op.create_index('ix_outcomes_recorded_by', 'outcomes', ['recorded_by'])

    # 5. One-to-one constraint: Enforce one outcome per decision
    op.create_unique_constraint('uq_outcomes_decision_id', 'outcomes', ['decision_id'])

    # 6. Update status check constraint to include Day 19 lifecycle statuses
    op.drop_constraint('ck_outcomes_status', 'outcomes', type_='check')
    op.create_check_constraint(
        'ck_outcomes_status',
        'outcomes',
        "outcome_status IN ('Success', 'Partial Success', 'Failure', 'Pending', 'RECORDED', 'DELIVERED', 'AWAITING_DELIVERY', 'CANCELLED', 'DISPUTED')"
    )

    # 7. Add validation check constraints
    op.create_check_constraint(
        'ck_outcomes_actual_delay',
        'outcomes',
        'actual_delay IS NULL OR actual_delay >= 0'
    )
    op.create_check_constraint(
        'ck_outcomes_actual_quantity',
        'outcomes',
        'actual_quantity IS NULL OR actual_quantity > 0'
    )


def downgrade() -> None:
    # 1. Drop check constraints
    op.drop_constraint('ck_outcomes_actual_quantity', 'outcomes', type_='check')
    op.drop_constraint('ck_outcomes_actual_delay', 'outcomes', type_='check')
    op.drop_constraint('ck_outcomes_status', 'outcomes', type_='check')

    # Re-apply original check constraint
    op.create_check_constraint(
        'ck_outcomes_status',
        'outcomes',
        "outcome_status IN ('Success', 'Partial Success', 'Failure', 'Pending')"
    )

    # 2. Drop unique constraint on decision_id
    op.drop_constraint('uq_outcomes_decision_id', 'outcomes', type_='unique')

    # 3. Drop indexes
    op.drop_index('ix_outcomes_recorded_by', table_name='outcomes')
    op.drop_index('ix_outcomes_decision_business_id', table_name='outcomes')
    op.drop_index('ix_outcomes_shipment_id', table_name='outcomes')

    # 4. Drop foreign key
    op.drop_constraint('fk_outcomes_shipment_id', 'outcomes', type_='foreignkey')

    # 5. Drop added columns
    op.drop_column('outcomes', 'updated_at')
    op.drop_column('outcomes', 'recorded_by')
    op.drop_column('outcomes', 'notes')
    op.drop_column('outcomes', 'source')
    op.drop_column('outcomes', 'actual_quantity')
    op.drop_column('outcomes', 'actual_supplier')
    op.drop_column('outcomes', 'baseline_delivery_date')
    op.drop_column('outcomes', 'actual_delay')
    op.drop_column('outcomes', 'currency')
    op.drop_column('outcomes', 'decision_business_id')
    op.drop_column('outcomes', 'shipment_id')
