from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

InventoryStatusType = Literal["Healthy", "Low", "Critical", "Out of Stock"]


class InventoryBase(BaseModel):
    product_id: str = Field(..., max_length=50)
    inventory_date: date
    inventory_level: int = Field(..., ge=0)
    demand: int = Field(..., ge=0)
    reorder_point: int = Field(..., ge=0)
    safety_stock: int = Field(..., ge=0)
    inventory_status: InventoryStatusType


class InventoryCreate(InventoryBase):
    pass


class InventoryResponse(InventoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
