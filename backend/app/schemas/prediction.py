from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field

PredictionType = Literal["Delay Risk", "Delivery Time", "Inventory Shortage", "Demand Forecast"]


class PredictionBase(BaseModel):
    prediction_id: str = Field(..., max_length=50)
    shipment_id: str = Field(..., max_length=50)
    model_version_id: int
    prediction_type: PredictionType
    predicted_value: Decimal
    prediction_probability: Optional[Decimal] = Field(None, ge=0, le=1)
    prediction_status: str = Field(default="Generated", max_length=50)
    prediction_date: Optional[datetime] = None
    prediction_horizon: Optional[int] = None


class PredictionCreate(PredictionBase):
    pass


class PredictionResponse(PredictionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
