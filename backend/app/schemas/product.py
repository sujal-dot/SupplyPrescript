from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    product_id: str = Field(..., max_length=50)
    product_name: str = Field(..., max_length=255)
    category: str = Field(..., max_length=100)
    unit_cost: Decimal = Field(..., gt=0)
    weight_kg: Decimal = Field(..., gt=0)
    base_demand: Decimal = Field(default=Decimal("0.0"), ge=0)


class ProductCreate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
