from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field

OutcomeStatusType = Literal["Success", "Partial Success", "Failure", "Pending"]


class OutcomeBase(BaseModel):
    outcome_id: str = Field(..., max_length=50)
    decision_id: int
    actual_delivery_date: Optional[date] = None
    actual_delay_days: int = Field(default=0, ge=0)
    actual_cost: Decimal = Field(default=Decimal("0.0"), ge=0)
    inventory_impact: Optional[int] = None
    outcome_status: OutcomeStatusType = "Pending"
    success_score: Optional[Decimal] = Field(None, ge=0, le=1)
    outcome_notes: Optional[str] = None


class OutcomeCreate(OutcomeBase):
    pass


class OutcomeResponse(OutcomeBase):
    id: int
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)
