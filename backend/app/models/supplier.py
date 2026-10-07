from sqlalchemy import Column, Integer, String, Numeric, DateTime, CheckConstraint, func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(String(50), unique=True, nullable=False, index=True)
    supplier_name = Column(String(255), nullable=False)
    origin = Column(String(100), nullable=False)
    supplier_reliability = Column(Numeric(5, 4), nullable=False, default=1.0000)
    base_lead_time = Column(Integer, nullable=True)
    capacity = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("supplier_reliability >= 0 AND supplier_reliability <= 1", name="ck_suppliers_supplier_reliability"),
        CheckConstraint("base_lead_time IS NULL OR base_lead_time > 0", name="ck_suppliers_base_lead_time"),
        CheckConstraint("capacity IS NULL OR capacity >= 0", name="ck_suppliers_capacity"),
    )

    # Relationships
    shipments = relationship("Shipment", back_populates="supplier")

    def __repr__(self):
        return f"<Supplier(supplier_id='{self.supplier_id}', name='{self.supplier_name}', reliability={self.supplier_reliability})>"
