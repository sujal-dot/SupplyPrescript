from datetime import date
from typing import Literal, Optional
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
    id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryListResponse(BaseModel):
    data: list[InventoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
