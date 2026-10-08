from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SupplierBase(BaseModel):
    supplier_id: str = Field(..., max_length=50)
    supplier_name: str = Field(..., max_length=255)
    origin: str = Field(..., max_length=100)
    supplier_reliability: Decimal = Field(default=Decimal("1.0000"), ge=0, le=1)
    base_lead_time: Optional[int] = Field(None, gt=0)
    capacity: Optional[int] = Field(None, ge=0)


class SupplierCreate(SupplierBase):
    pass


class SupplierResponse(SupplierBase):
    id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class SupplierListResponse(BaseModel):
    data: list[SupplierResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
