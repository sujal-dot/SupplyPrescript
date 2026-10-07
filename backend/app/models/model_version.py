from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database.connection import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    model_type = Column(String(100), nullable=False)
    algorithm = Column(String(100), nullable=False)
    training_date = Column(DateTime(timezone=True), nullable=True)
    dataset_version = Column(String(50), nullable=True)
    metrics = Column(JSONB, nullable=True)
    model_path = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("model_name", "version", name="uq_model_versions_name_version"),
    )

    # Relationships
    predictions = relationship("Prediction", back_populates="model_version")

    def __repr__(self):
        return f"<ModelVersion(model_name='{self.model_name}', version='{self.version}', active={self.is_active})>"
