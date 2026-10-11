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


# ---------------------------------------------------------------------------
# ML Inference Request and Response Schemas (Day 7)
# ---------------------------------------------------------------------------
class ShipmentPredictionRequest(BaseModel):
    supplier_reliability: float = Field(..., ge=0.0, le=1.0, description="Known supplier reliability score [0.0, 1.0]")
    historical_avg_delay: float = Field(..., ge=0.0, description="Empirical prior average delay days of the supplier")
    lead_time: int = Field(..., gt=0, description="Planned transit lead time in days (expected - order)")
    inventory_level: int = Field(..., ge=0, description="Available inventory on hand at order placement")
    demand: int = Field(..., ge=0, description="Projected SKU demand at order placement")
    quantity: int = Field(..., gt=0, description="Order quantity")
    shipping_cost: float = Field(..., ge=0.0, description="Contracted shipping freight cost")
    transport_mode: Literal["Road", "Rail", "Air", "Sea"] = Field(..., description="Transit modality")
    season: Literal["Winter", "Summer", "Monsoon", "Post-Monsoon"] = Field(..., description="Meteorological order season")
    priority: Literal["Low", "Medium", "High", "Critical"] = Field(..., description="Shipment priority rating")
    distance: float = Field(..., gt=0.0, description="Estimated transit route distance in km")


class ShipmentPredictionResult(BaseModel):
    delayed: bool = Field(..., description="Predicted binary delay status (True = delayed, False = on-time)")
    delay_probability: float = Field(..., ge=0.0, le=1.0, description="Predicted probability of delay [0.0, 1.0]")
    predicted_delay_days: float = Field(..., ge=0.0, description="Predicted number of delay days (non-negative)")
    classification_threshold: float = Field(..., description="Classification decision boundary threshold applied")
    model_version: str = Field(..., description="Active version of classification and regression models")
    disagreement_warning: Optional[str] = Field(None, description="Warning if classification and regression predictions diverge")
    prediction_timestamp: str = Field(..., description="ISO 8601 UTC timestamp of prediction generation")
