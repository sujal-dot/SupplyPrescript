from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(String(50), unique=True, nullable=False, index=True)
    supplier_id = Column(String(50), ForeignKey("suppliers.supplier_id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id = Column(String(50), ForeignKey("products.product_id", ondelete="RESTRICT"), nullable=False, index=True)
    origin = Column(String(100), nullable=False)
    destination = Column(String(100), nullable=False)
    order_date = Column(Date, nullable=False, index=True)
    expected_delivery_date = Column(Date, nullable=False)
    actual_delivery_date = Column(Date, nullable=False, index=True)
    lead_time = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(10, 2), nullable=False)
    shipping_cost = Column(Numeric(10, 2), nullable=False)
    supplier_reliability = Column(Numeric(5, 4), nullable=False)
    inventory_level = Column(Integer, nullable=False)
    demand = Column(Integer, nullable=False)
    priority = Column(String(50), nullable=False)
    transport_mode = Column(String(50), nullable=False)
    delay_days = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_shipments_quantity"),
        CheckConstraint("unit_cost > 0", name="ck_shipments_unit_cost"),
        CheckConstraint("shipping_cost >= 0", name="ck_shipments_shipping_cost"),
        CheckConstraint("supplier_reliability >= 0 AND supplier_reliability <= 1", name="ck_shipments_supplier_reliability"),
        CheckConstraint("inventory_level >= 0", name="ck_shipments_inventory_level"),
        CheckConstraint("demand >= 0", name="ck_shipments_demand"),
        CheckConstraint("lead_time > 0", name="ck_shipments_lead_time"),
        CheckConstraint("delay_days >= 0", name="ck_shipments_delay_days"),
        CheckConstraint("order_date <= expected_delivery_date", name="ck_shipments_order_expected_date"),
        CheckConstraint("order_date <= actual_delivery_date", name="ck_shipments_order_actual_date"),
    )

    # Relationships
    supplier = relationship("Supplier", back_populates="shipments")
    product = relationship("Product", back_populates="shipments")
    predictions = relationship("Prediction", back_populates="shipment")

    def __repr__(self):
        return f"<Shipment(shipment_id='{self.shipment_id}', supplier='{self.supplier_id}', product='{self.product_id}', delay_days={self.delay_days})>"
