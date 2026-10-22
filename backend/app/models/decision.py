from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint,
    Numeric, JSON, func
)
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(String(50), unique=True, nullable=False, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id", ondelete="RESTRICT"), nullable=False, index=True)
    decision = Column(String(255), nullable=False)
    decision_reason = Column(Text, nullable=True)
    decision_source = Column(String(50), nullable=False)
    approved_by = Column(String(100), nullable=True)
    decision_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(50), nullable=False, default="Pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Day 17 Decision Execution & Governance fields
    shipment_id = Column(String(50), ForeignKey("shipments.shipment_id", ondelete="SET NULL"), nullable=True, index=True)
    optimization_run_id = Column(String(50), nullable=True, index=True)
    option_id = Column(String(10), nullable=True)
    strategy = Column(String(50), nullable=True)
    estimated_total_cost = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(10), nullable=True, default="USD")
    estimated_delivery_days = Column(Numeric(6, 2), nullable=True)
    delay_probability = Column(Numeric(5, 4), nullable=True)
    constraint_validation_snapshot = Column(JSON, nullable=True)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=True)
    external_action_status = Column(String(50), nullable=True, default="NOT_EXECUTED")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Day 18 Write-Back Architecture fields
    user_id = Column(String(100), nullable=True, index=True)
    predicted_cost = Column(Numeric(12, 2), nullable=True)
    predicted_delay = Column(Numeric(6, 2), nullable=True)
    decision_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('Pending', 'Approved', 'Rejected', 'Executed', 'Cancelled', 'RECORDED', 'PENDING_CONFIRMATION', 'FAILED')",
            name="ck_decisions_status",
        ),
        CheckConstraint(
            "decision_source IN ('AI', 'Human', 'Rule', 'Optimization')",
            name="ck_decisions_source",
        ),
    )

    # Relationships
    recommendation = relationship("Recommendation", back_populates="decisions")
    outcomes = relationship("Outcome", back_populates="decision")

    @property
    def outcome(self):
        """Convenience property for single associated outcome."""
        return self.outcomes[0] if self.outcomes else None

    def __repr__(self):
        return f"<Decision(decision_id='{self.decision_id}', decision='{self.decision}', source='{self.decision_source}', status='{self.status}')>"
