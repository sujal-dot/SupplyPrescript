from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShipmentBase(BaseModel):
    shipment_id: str = Field(..., max_length=50)
    supplier_id: str = Field(..., max_length=50)
    product_id: str = Field(..., max_length=50)
    origin: str = Field(..., max_length=100)
    destination: str = Field(..., max_length=100)
    order_date: date
    expected_delivery_date: date
    actual_delivery_date: date
    lead_time: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    unit_cost: Decimal = Field(..., gt=0)
    shipping_cost: Decimal = Field(..., ge=0)
    supplier_reliability: Decimal = Field(..., ge=0, le=1)
    inventory_level: int = Field(..., ge=0)
    demand: int = Field(..., ge=0)
    priority: str = Field(..., max_length=50)
    transport_mode: str = Field(..., max_length=50)
    delay_days: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.order_date > self.expected_delivery_date:
            raise ValueError("order_date must be less than or equal to expected_delivery_date")
        if self.order_date > self.actual_delivery_date:
            raise ValueError("order_date must be less than or equal to actual_delivery_date")
        return self


class ShipmentCreate(ShipmentBase):
    pass


class ShipmentResponse(ShipmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
