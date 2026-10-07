from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(50), ForeignKey("products.product_id", ondelete="RESTRICT"), nullable=False, index=True)
    inventory_date = Column(Date, nullable=False, index=True)
    inventory_level = Column(Integer, nullable=False)
    demand = Column(Integer, nullable=False)
    reorder_point = Column(Integer, nullable=False)
    safety_stock = Column(Integer, nullable=False)
    inventory_status = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("inventory_level >= 0", name="ck_inventory_level"),
        CheckConstraint("demand >= 0", name="ck_inventory_demand"),
        CheckConstraint("reorder_point >= 0", name="ck_inventory_reorder_point"),
        CheckConstraint("safety_stock >= 0", name="ck_inventory_safety_stock"),
        CheckConstraint("inventory_status IN ('Healthy', 'Low', 'Critical', 'Out of Stock')", name="ck_inventory_status"),
    )

    # Relationships
    product = relationship("Product", back_populates="inventory")

    def __repr__(self):
        return f"<Inventory(product_id='{self.product_id}', date='{self.inventory_date}', level={self.inventory_level}, status='{self.inventory_status}')>"
