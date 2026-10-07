from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint, func
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

    __table_args__ = (
        CheckConstraint("status IN ('Pending', 'Approved', 'Rejected', 'Executed', 'Cancelled')", name="ck_decisions_status"),
        CheckConstraint("decision_source IN ('AI', 'Human', 'Rule', 'Optimization')", name="ck_decisions_source"),
    )

    # Relationships
    recommendation = relationship("Recommendation", back_populates="decisions")
    outcomes = relationship("Outcome", back_populates="decision")

    def __repr__(self):
        return f"<Decision(decision_id='{self.decision_id}', decision='{self.decision}', source='{self.decision_source}', status='{self.status}')>"
