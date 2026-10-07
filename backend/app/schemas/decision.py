from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field

DecisionStatusType = Literal["Pending", "Approved", "Rejected", "Executed", "Cancelled"]
DecisionSourceType = Literal["AI", "Human", "Rule", "Optimization"]


class DecisionBase(BaseModel):
    decision_id: str = Field(..., max_length=50)
    recommendation_id: int
    decision: str = Field(..., max_length=255)
    decision_reason: Optional[str] = None
    decision_source: DecisionSourceType
    approved_by: Optional[str] = Field(None, max_length=100)
    decision_date: Optional[datetime] = None
    status: DecisionStatusType = "Pending"


class DecisionCreate(DecisionBase):
    pass


class DecisionResponse(DecisionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
