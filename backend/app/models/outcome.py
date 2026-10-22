from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Date, DateTime, ForeignKey,
    CheckConstraint, UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    outcome_id = Column(String(50), unique=True, nullable=False, index=True)
    decision_id = Column(Integer, ForeignKey("decisions.id", ondelete="RESTRICT"), unique=True, nullable=False, index=True)
    decision_business_id = Column(String(64), nullable=True, index=True)
    shipment_id = Column(String(50), ForeignKey("shipments.shipment_id", ondelete="SET NULL"), nullable=True, index=True)

    # Financial & Delivery Actuals
    actual_cost = Column(Numeric(12, 2), nullable=False, default=0.0)
    currency = Column(String(10), nullable=True, default="USD")
    actual_delivery_date = Column(Date, nullable=True)
    actual_delay = Column(Numeric(6, 2), nullable=True)
    actual_delay_days = Column(Integer, nullable=False, default=0)
    baseline_delivery_date = Column(Date, nullable=True)

    # Operational Execution Actuals
    actual_supplier = Column(String(100), nullable=True)
    actual_quantity = Column(Numeric(10, 2), nullable=True)

    # Lifecycle & Governance Metadata
    outcome_status = Column(String(50), nullable=False, default="RECORDED")
    source = Column(String(50), nullable=True, default="manual_entry")
    notes = Column(Text, nullable=True)
    outcome_notes = Column(Text, nullable=True)
    recorded_by = Column(String(100), nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Legacy / Analytics fields
    inventory_impact = Column(Integer, nullable=True)
    success_score = Column(Numeric(5, 4), nullable=True)

    __table_args__ = (
        UniqueConstraint("decision_id", name="uq_outcomes_decision_id"),
        CheckConstraint("actual_cost >= 0", name="ck_outcomes_actual_cost"),
        CheckConstraint("actual_delay_days >= 0", name="ck_outcomes_actual_delay_days"),
        CheckConstraint("actual_delay IS NULL OR actual_delay >= 0", name="ck_outcomes_actual_delay"),
        CheckConstraint("actual_quantity IS NULL OR actual_quantity > 0", name="ck_outcomes_actual_quantity"),
        CheckConstraint("success_score IS NULL OR (success_score >= 0 AND success_score <= 1)", name="ck_outcomes_success_score"),
        CheckConstraint(
            "outcome_status IN ('Success', 'Partial Success', 'Failure', 'Pending', 'RECORDED', 'DELIVERED', 'AWAITING_DELIVERY', 'CANCELLED', 'DISPUTED')",
            name="ck_outcomes_status",
        ),
    )

    # Relationships
    decision = relationship("Decision", back_populates="outcomes")
    shipment = relationship("Shipment", foreign_keys=[shipment_id])

    def __repr__(self):
        return (
            f"<Outcome(outcome_id='{self.outcome_id}', "
            f"decision='{self.decision_business_id or self.decision_id}', "
            f"status='{self.outcome_status}', "
            f"actual_cost={self.actual_cost})>"
        )
