"""SupplyPrescript — Model Feedback Database Model (Day 22)
=========================================================
Tracks original delay predictions linked to actual operational delivery outcomes,
calculates signed and absolute prediction errors, validates eligibility, and maintains
versioned feedback observations for model continuous learning.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Numeric, DateTime, ForeignKey,
    CheckConstraint, UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Feedback(Base):
    __tablename__ = "model_feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feedback_id = Column(String(50), unique=True, nullable=False, index=True)
    prediction_id = Column(String(50), unique=True, nullable=False, index=True)
    shipment_id = Column(String(50), ForeignKey("shipments.shipment_id", ondelete="SET NULL"), nullable=True, index=True)
    decision_id = Column(String(50), nullable=True, index=True)

    # Predictions & Actuals
    predicted_delay = Column(Numeric(6, 2), nullable=False)
    actual_delay = Column(Numeric(6, 2), nullable=True)
    prediction_error = Column(Numeric(6, 2), nullable=True)  # actual_delay - predicted_delay
    absolute_error = Column(Numeric(6, 2), nullable=True)    # abs(actual_delay - predicted_delay)

    # Timestamps & Lineage
    prediction_timestamp = Column(DateTime(timezone=True), nullable=False)
    outcome_timestamp = Column(DateTime(timezone=True), nullable=True)
    model_version = Column(String(50), nullable=False, index=True)

    # Pipeline Governance & Dataset Versioning
    feedback_status = Column(String(50), nullable=False, default="PENDING_OUTCOME", index=True)
    exclusion_reason = Column(String(255), nullable=True)
    dataset_version = Column(String(50), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "feedback_status IN ('ELIGIBLE', 'PENDING_OUTCOME', 'EXCLUDED', 'UNDER_REVIEW')",
            name="ck_model_feedbacks_status",
        ),
        CheckConstraint(
            "absolute_error IS NULL OR absolute_error >= 0",
            name="ck_model_feedbacks_absolute_error",
        ),
        UniqueConstraint("prediction_id", name="uq_model_feedbacks_prediction_id"),
    )

    # Relationships
    shipment = relationship("Shipment", foreign_keys=[shipment_id])

    def __repr__(self):
        return (
            f"<Feedback(feedback_id='{self.feedback_id}', prediction_id='{self.prediction_id}', "
            f"shipment_id='{self.shipment_id}', error={self.prediction_error}, status='{self.feedback_status}')>"
        )
