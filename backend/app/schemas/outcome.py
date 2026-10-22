"""SupplyPrescript — Closed-Loop Outcome Schemas (Day 19)
=========================================================
Pydantic schemas for recording operational actuals and retrieving predicted vs actual comparisons.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field

# Legacy outcome status literal for backward compatibility
LegacyOutcomeStatusType = Literal["Success", "Partial Success", "Failure", "Pending"]

# Day 19 extended outcome lifecycle status
OutcomeStatusType = Literal[
    "RECORDED",
    "DELIVERED",
    "AWAITING_DELIVERY",
    "CANCELLED",
    "DISPUTED",
    "Success",
    "Partial Success",
    "Failure",
    "Pending",
]


class OutcomeBase(BaseModel):
    outcome_id: str = Field(..., max_length=50)
    decision_id: Any
    actual_delivery_date: Optional[date] = None
    actual_delay_days: int = Field(default=0, ge=0)
    actual_cost: Decimal = Field(default=Decimal("0.0"), ge=0)
    inventory_impact: Optional[int] = None
    outcome_status: str = "Pending"
    success_score: Optional[Decimal] = Field(None, ge=0, le=1)
    outcome_notes: Optional[str] = None


class OutcomeCreate(OutcomeBase):
    pass


class OutcomeResponse(OutcomeBase):
    id: int
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Day 19 Outcome Tracking & Comparison Schemas
# ==========================================

class RecordOutcomeRequest(BaseModel):
    """Payload to record an actual operational outcome for a decision."""
    actual_cost: Decimal = Field(..., ge=0, description="Actual cost incurred for the decision.")
    currency: Optional[str] = Field("USD", max_length=10, description="Currency code (default USD).")
    actual_delivery_date: Optional[date] = Field(None, description="Actual delivery date if delivered.")
    actual_delay: Optional[Decimal] = Field(None, ge=0, description="Actual delay in days (auto-calculated if omitted).")
    baseline_delivery_date: Optional[date] = Field(None, description="Agreed baseline delivery date (retrieved from shipment if omitted).")
    actual_supplier: Optional[str] = Field(None, max_length=100, description="Supplier that actually fulfilled the order.")
    actual_quantity: Optional[Decimal] = Field(None, gt=0, description="Quantity actually supplied or delivered.")
    outcome_status: Optional[str] = Field(None, description="Lifecycle status of outcome (default DELIVERED if delivered, else RECORDED).")
    source: Optional[str] = Field("manual_entry", max_length=50, description="Data source (e.g. manual_entry, erp_invoice, carrier_webhook).")
    notes: Optional[str] = Field(None, description="Operational explanation for cost/delivery variances.")
    recorded_by: Optional[str] = Field(None, max_length=100, description="Identifier of actor recording outcome.")

    model_config = ConfigDict(extra="ignore")


class OutcomeRecordResponse(BaseModel):
    """Authoritative operational outcome record schema."""
    outcome_id: str
    decision_id: str
    shipment_id: Optional[str] = None
    actual_cost: Decimal
    currency: str = "USD"
    actual_delivery_date: Optional[date] = None
    actual_delay: Optional[Decimal] = None
    baseline_delivery_date: Optional[date] = None
    actual_supplier: Optional[str] = None
    actual_quantity: Optional[Decimal] = None
    outcome_status: str = "RECORDED"
    source: str = "manual_entry"
    notes: Optional[str] = None
    recorded_by: Optional[str] = None
    recorded_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PredictedSnapshot(BaseModel):
    predicted_cost: Optional[float] = None
    predicted_delay: Optional[float] = None
    predicted_delivery_date: Optional[str] = None
    planned_quantity: Optional[float] = None
    planned_supplier: Optional[str] = None
    currency: str = "USD"


class ActualSnapshot(BaseModel):
    outcome_id: Optional[str] = None
    actual_cost: Optional[float] = None
    actual_delay: Optional[float] = None
    actual_delivery_date: Optional[str] = None
    actual_quantity: Optional[float] = None
    actual_supplier: Optional[str] = None
    currency: str = "USD"
    outcome_status: str = "RECORDED"
    source: str = "manual_entry"
    recorded_at: Optional[str] = None


class VarianceMetrics(BaseModel):
    cost_variance: Optional[float] = Field(None, description="actual_cost - predicted_cost")
    cost_variance_percentage: Optional[float] = Field(None, description="Cost variance percentage")
    delay_variance: Optional[float] = Field(None, description="actual_delay - predicted_delay (days)")
    delivery_date_variance_days: Optional[int] = Field(None, description="actual_delivery_date - predicted_delivery_date (days)")
    quantity_variance: Optional[float] = Field(None, description="actual_quantity - planned_quantity")
    supplier_matched: Optional[bool] = Field(None, description="Whether actual supplier matches planned supplier")


class OutcomeComparisonResponse(BaseModel):
    """Complete closed-loop comparison response."""
    decision_id: str
    shipment_id: Optional[str] = None
    predicted: PredictedSnapshot
    actual: Optional[ActualSnapshot] = None
    variance: Optional[VarianceMetrics] = None
    data_completeness: str = Field(..., description="COMPLETE, PARTIAL, or NO_OUTCOME")
    notes: List[str] = Field(default_factory=list)
    outcome: Optional[OutcomeRecordResponse] = None


class OutcomeListResponse(BaseModel):
    """Paginated list of recorded outcomes."""
    total: int
    limit: int
    offset: int
    items: List[OutcomeRecordResponse]
