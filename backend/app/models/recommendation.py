from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(String(50), unique=True, nullable=False, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id", ondelete="RESTRICT"), nullable=False, index=True)
    recommendation_type = Column(String(100), nullable=False)
    recommendation_text = Column(Text, nullable=False)
    recommended_action = Column(String(255), nullable=False)
    priority = Column(String(50), nullable=False, default="Medium")
    confidence_score = Column(Numeric(5, 4), nullable=False)
    status = Column(String(50), nullable=False, default="Active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="ck_recommendations_confidence_score"),
        CheckConstraint(
            "recommendation_type IN ('Expedite Shipment', 'Change Supplier', 'Increase Inventory', 'Reduce Order Quantity', 'Reorder Inventory', 'Monitor Supplier')",
            name="ck_recommendations_type"
        ),
    )

    # Relationships
    prediction = relationship("Prediction", back_populates="recommendations")
    decisions = relationship("Decision", back_populates="recommendation")

    def __repr__(self):
        return f"<Recommendation(recommendation_id='{self.recommendation_id}', type='{self.recommendation_type}', priority='{self.priority}')>"
