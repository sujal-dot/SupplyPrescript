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


# ---------------------------------------------------------------------------
# Day 9 Production Prediction Endpoint Schemas (POST /api/predict)
# ---------------------------------------------------------------------------
from typing import Dict, Any
from pydantic import field_validator, model_validator

VALID_MODES_MAP: Dict[str, str] = {
    "road": "Road",
    "rail": "Rail",
    "air": "Air",
    "sea": "Sea",
}

VALID_PRIORITIES_MAP: Dict[str, str] = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "critical": "Critical",
}

VALID_SEASONS_MAP: Dict[str, str] = {
    "winter": "Winter",
    "summer": "Summer",
    "monsoon": "Monsoon",
    "post-monsoon": "Post-Monsoon",
}

LEAKAGE_FORBIDDEN_FIELDS = {
    "actual_delivery_date",
    "actual_delay_days",
    "delay_days",
    "delayed",
    "is_delayed",
    "delivery_status",
    "delay_reason",
    "outcome",
    "success_score",
    "lead_time_outlier",
}

RiskCategory = Literal["LOW", "MEDIUM", "HIGH"]


def determine_risk_category(
    delay_probability: float,
    low_threshold: float = 0.30,
    high_threshold: float = 0.70,
) -> RiskCategory:
    """
    Categorize delay risk based on predicted delay probability:
    - Below 0.30: LOW
    - 0.30 to below 0.70: MEDIUM
    - 0.70 to 1.00: HIGH
    
    Consistent boundary behavior:
    - 0.2999 -> LOW
    - 0.30   -> MEDIUM
    - 0.6999 -> MEDIUM
    - 0.70   -> HIGH
    - 1.0    -> HIGH
    """
    if delay_probability < low_threshold:
        return "LOW"
    elif delay_probability < high_threshold:
        return "MEDIUM"
    else:
        return "HIGH"


class PredictRequest(BaseModel):
    """
    Incoming request schema for shipment delay risk prediction.
    Requires essential shipment details and scenario inputs. Missing model features
    are resolved from the authoritative database (suppliers, products, inventory).
    """
    supplier_id: int = Field(..., gt=0, description="Supplier database ID (positive integer)")
    product_id: int = Field(..., gt=0, description="Product database ID (positive integer)")
    quantity: int = Field(..., gt=0, description="Shipment order quantity (must be > 0)")
    inventory_level: int = Field(..., ge=0, description="Available inventory scenario at order time (non-negative integer)")
    transport_mode: str = Field(..., description="Transit modality: Road, Rail, Air, or Sea (case-insensitive)")

    # Optional scenario planning parameters
    destination: Optional[str] = Field(None, description="Optional destination city hub")
    shipping_cost: Optional[float] = Field(None, ge=0.0, description="Optional contracted freight shipping cost (non-negative)")
    priority: Optional[str] = Field(None, description="Optional shipment priority: Low, Medium, High, Critical")
    lead_time: Optional[int] = Field(None, gt=0, description="Optional planned transit lead time in days (> 0)")
    season: Optional[str] = Field(None, description="Optional meteorological season: Winter, Summer, Monsoon, Post-Monsoon")
    demand: Optional[int] = Field(None, ge=0, description="Optional projected SKU market demand scenario (non-negative)")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "supplier_id": 12,
                "product_id": 45,
                "quantity": 500,
                "inventory_level": 1200,
                "transport_mode": "air"
            }
        }
    )

    @field_validator("transport_mode")
    @classmethod
    def validate_and_normalize_transport_mode(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("transport_mode must be a non-empty string")
        clean = v.strip().lower()
        if clean not in VALID_MODES_MAP:
            raise ValueError(
                f"Invalid transport_mode: '{v}'. Supported modes are: Road, Rail, Air, Sea."
            )
        return VALID_MODES_MAP[clean]

    @field_validator("priority")
    @classmethod
    def validate_and_normalize_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip().lower()
        if clean not in VALID_PRIORITIES_MAP:
            raise ValueError(
                f"Invalid priority: '{v}'. Supported priorities are: Low, Medium, High, Critical."
            )
        return VALID_PRIORITIES_MAP[clean]

    @field_validator("season")
    @classmethod
    def validate_and_normalize_season(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip().lower()
        if clean not in VALID_SEASONS_MAP:
            raise ValueError(
                f"Invalid season: '{v}'. Supported seasons are: Winter, Summer, Monsoon, Post-Monsoon."
            )
        return VALID_SEASONS_MAP[clean]

    @model_validator(mode="before")
    @classmethod
    def reject_target_leakage_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            found_leakage = [k for k in values.keys() if k.lower() in LEAKAGE_FORBIDDEN_FIELDS]
            if found_leakage:
                raise ValueError(
                    f"Target leakage or outcome fields are forbidden in prediction requests: {found_leakage}"
                )
        return values


class PredictResponse(BaseModel):
    """
    Standardized response payload for shipment delay risk prediction.
    Returns delay probability, predicted delay duration in days, and risk tier.
    """
    delay_probability: float = Field(..., ge=0.0, le=1.0, description="Predicted probability of shipment delay [0.0, 1.0]")
    predicted_delay_days: float = Field(..., ge=0.0, description="Predicted delay duration in days (non-negative float)")
    risk: RiskCategory = Field(..., description="Operational risk tier: LOW (<0.30), MEDIUM (0.30 to <0.70), HIGH (>=0.70)")
    model_version: str = Field("v1.0", description="Active registered ML model version used for inference")
    prediction_id: Optional[str] = Field(None, description="Unique prediction UUID for audit tracking")
    prediction_timestamp: str = Field(..., description="ISO 8601 UTC timestamp of inference execution")
    features_used: Optional[Dict[str, Any]] = Field(None, description="Resolved feature vector supplied to ML model")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "delay_probability": 0.87,
                "predicted_delay_days": 14.0,
                "risk": "HIGH",
                "model_version": "v1.0",
                "prediction_id": "PRED-1A2B3C4D5E6F",
                "prediction_timestamp": "2026-10-12T10:00:00Z"
            }
        }
    )


class StoredPredictionItem(BaseModel):
    id: int
    prediction_id: str
    shipment_id: str
    supplier_id: Optional[str] = None
    product_id: Optional[str] = None
    prediction_type: str
    predicted_value: float
    prediction_probability: Optional[float] = None
    risk: str
    model_version: str
    prediction_status: str
    prediction_date: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoredPredictionListResponse(BaseModel):
    data: list[StoredPredictionItem]
    total: int
    page: int
    page_size: int
    total_pages: int
