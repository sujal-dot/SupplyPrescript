from sqlalchemy import Column, Integer, String, Text, Numeric, Date, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    outcome_id = Column(String(50), unique=True, nullable=False, index=True)
    decision_id = Column(Integer, ForeignKey("decisions.id", ondelete="RESTRICT"), nullable=False, index=True)
    actual_delivery_date = Column(Date, nullable=True)
    actual_delay_days = Column(Integer, nullable=False, default=0)
    actual_cost = Column(Numeric(10, 2), nullable=False, default=0.0)
    inventory_impact = Column(Integer, nullable=True)
    outcome_status = Column(String(50), nullable=False, default="Pending")
    success_score = Column(Numeric(5, 4), nullable=True)
    outcome_notes = Column(Text, nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("actual_delay_days >= 0", name="ck_outcomes_actual_delay_days"),
        CheckConstraint("actual_cost >= 0", name="ck_outcomes_actual_cost"),
        CheckConstraint("success_score IS NULL OR (success_score >= 0 AND success_score <= 1)", name="ck_outcomes_success_score"),
        CheckConstraint("outcome_status IN ('Success', 'Partial Success', 'Failure', 'Pending')", name="ck_outcomes_status"),
    )

    # Relationships
    decision = relationship("Decision", back_populates="outcomes")

    def __repr__(self):
        return f"<Outcome(outcome_id='{self.outcome_id}', status='{self.outcome_status}', success_score={self.success_score})>"
