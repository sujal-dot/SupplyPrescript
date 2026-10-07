from sqlalchemy import Column, Integer, String, Numeric, DateTime, CheckConstraint, func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(50), unique=True, nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    unit_cost = Column(Numeric(10, 2), nullable=False)
    weight_kg = Column(Numeric(10, 2), nullable=False)
    base_demand = Column(Numeric(10, 2), nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("unit_cost > 0", name="ck_products_unit_cost"),
        CheckConstraint("weight_kg > 0", name="ck_products_weight_kg"),
        CheckConstraint("base_demand >= 0", name="ck_products_base_demand"),
    )

    # Relationships
    shipments = relationship("Shipment", back_populates="product")
    inventory = relationship("Inventory", back_populates="product")

    def __repr__(self):
        return f"<Product(product_id='{self.product_id}', name='{self.product_name}', category='{self.category}')>"
