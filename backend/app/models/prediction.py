from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(String(50), unique=True, nullable=False, index=True)
    shipment_id = Column(String(50), ForeignKey("shipments.shipment_id", ondelete="RESTRICT"), nullable=False, index=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    prediction_type = Column(String(100), nullable=False)
    predicted_value = Column(Numeric(10, 4), nullable=False)
    prediction_probability = Column(Numeric(5, 4), nullable=True)
    prediction_status = Column(String(50), nullable=False, default="Generated")
    prediction_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    prediction_horizon = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "prediction_probability IS NULL OR (prediction_probability >= 0 AND prediction_probability <= 1)",
            name="ck_predictions_probability"
        ),
        CheckConstraint(
            "prediction_type IN ('Delay Risk', 'Delivery Time', 'Inventory Shortage', 'Demand Forecast')",
            name="ck_predictions_type"
        ),
    )

    # Relationships
    shipment = relationship("Shipment", back_populates="predictions")
    model_version = relationship("ModelVersion", back_populates="predictions")
    recommendations = relationship("Recommendation", back_populates="prediction")

    def __repr__(self):
        return f"<Prediction(prediction_id='{self.prediction_id}', shipment_id='{self.shipment_id}', type='{self.prediction_type}', value={self.predicted_value})>"
