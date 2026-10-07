from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

RecommendationType = Literal[
    "Expedite Shipment",
    "Change Supplier",
    "Increase Inventory",
    "Reduce Order Quantity",
    "Reorder Inventory",
    "Monitor Supplier",
]


class RecommendationBase(BaseModel):
    recommendation_id: str = Field(..., max_length=50)
    prediction_id: int
    recommendation_type: RecommendationType
    recommendation_text: str
    recommended_action: str = Field(..., max_length=255)
    priority: str = Field(default="Medium", max_length=50)
    confidence_score: Decimal = Field(..., ge=0, le=1)
    status: str = Field(default="Active", max_length=50)


class RecommendationCreate(RecommendationBase):
    pass


class RecommendationResponse(RecommendationBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
