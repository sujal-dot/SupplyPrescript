"""add_write_back_fields

Revision ID: 21e279b9475a
Revises: 8795e41f3816
Create Date: 2026-10-22 11:31:07.459808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21e279b9475a'
down_revision: Union[str, None] = '8795e41f3816'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add write-back contract columns (Day 18)
    # Note: 'recommendation' is an existing ORM relationship pointing to recommendations.id;
    # strategy maps to the selected recommendation at the API/data contract level.
    op.add_column('decisions', sa.Column('user_id', sa.String(length=100), nullable=True))
    op.add_column('decisions', sa.Column('predicted_cost', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('decisions', sa.Column('predicted_delay', sa.Numeric(precision=6, scale=2), nullable=True))
    op.add_column('decisions', sa.Column('decision_time', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))

    # 2. Backfill existing rows from existing decision fields
    op.execute("""
        UPDATE decisions 
        SET predicted_cost = estimated_total_cost,
            decision_time = COALESCE(created_at, decision_date, CURRENT_TIMESTAMP),
            user_id = COALESCE(approved_by, 'usr_ops_manager')
        WHERE predicted_cost IS NULL OR decision_time IS NULL;
    """)

    # 3. Alter decision_time to NOT NULL now that it is backfilled
    op.alter_column('decisions', 'decision_time', nullable=False)

    # 4. Create indexes for performance on write-back query filters
    op.create_index('ix_decisions_user_id', 'decisions', ['user_id'], unique=False)
    op.create_index('ix_decisions_decision_time', 'decisions', ['decision_time'], unique=False)

    # 5. Add foreign key from decisions.shipment_id to shipments.shipment_id
    op.create_foreign_key(
        'fk_decisions_shipment_id',
        'decisions',
        'shipments',
        ['shipment_id'],
        ['shipment_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_decisions_shipment_id', 'decisions', type_='foreignkey')
    op.drop_index('ix_decisions_decision_time', table_name='decisions')
    op.drop_index('ix_decisions_user_id', table_name='decisions')
    op.drop_column('decisions', 'decision_time')
    op.drop_column('decisions', 'predicted_delay')
    op.drop_column('decisions', 'predicted_cost')
    op.drop_column('decisions', 'user_id')
