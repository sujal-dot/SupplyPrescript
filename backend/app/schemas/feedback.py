"""SupplyPrescript — Model Feedback Schemas (Day 22)
=================================================
Pydantic v2 schemas for prediction feedback generation, feedback item inspection,
versioned dataset manifests, and continuous model performance evaluation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field


FeedbackStatusType = Literal["ELIGIBLE", "PENDING_OUTCOME", "EXCLUDED", "UNDER_REVIEW"]


class FeedbackItemResponse(BaseModel):
    """Single prediction-outcome feedback record."""
    feedback_id: str = Field(..., description="Unique feedback observation identifier")
    prediction_id: str = Field(..., description="Original prediction identifier")
    shipment_id: Optional[str] = Field(None, description="Target shipment identifier")
    decision_id: Optional[str] = Field(None, description="Associated decision identifier if applicable")
    predicted_delay: float = Field(..., description="Delay in days predicted by model")
    actual_delay: Optional[float] = Field(None, description="Final observed delivery delay in days")
    prediction_error: Optional[float] = Field(None, description="actual_delay - predicted_delay (positive = arrived later)")
    absolute_error: Optional[float] = Field(None, description="abs(actual_delay - predicted_delay)")
    prediction_timestamp: datetime = Field(..., description="Timestamp when prediction was generated")
    outcome_timestamp: Optional[datetime] = Field(None, description="Timestamp when outcome was recorded")
    model_version: str = Field(..., description="Exact model version that generated prediction")
    feedback_status: FeedbackStatusType = Field(..., description="Eligibility status for model evaluation")
    exclusion_reason: Optional[str] = Field(None, description="Detailed rationale if excluded or under review")
    dataset_version: Optional[str] = Field(None, description="Feedback dataset version snapshot")
    notes: Optional[str] = Field(None, description="Audit or operational notes")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class FeedbackSummaryCounts(BaseModel):
    """Aggregate counts of feedback pipeline records."""
    total: int = Field(0, description="Total feedback records")
    eligible: int = Field(0, description="Records eligible for model evaluation")
    pending_outcome: int = Field(0, description="Predictions awaiting shipment delivery actuals")
    excluded: int = Field(0, description="Records excluded from evaluation due to data quality")
    under_review: int = Field(0, description="Records flagged for manual operator review")
    mean_absolute_error: Optional[float] = Field(None, description="Overall MAE across all eligible records")
    mean_signed_error: Optional[float] = Field(None, description="Overall directional bias across eligible records")

    model_config = ConfigDict(extra="ignore")


class FeedbackListResponse(BaseModel):
    """Paginated collection of feedback records with pipeline summary."""
    items: List[FeedbackItemResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total items matching filter")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Page size limit")
    total_pages: int = Field(..., description="Total number of pages")
    summary_counts: FeedbackSummaryCounts = Field(..., description="Status breakdown counts")

    model_config = ConfigDict(extra="ignore")


class GenerateFeedbackRequest(BaseModel):
    """Request payload to generate or refresh feedback dataset."""
    dataset_version: Optional[str] = Field(None, description="Optional custom dataset version label (e.g. FB_20261025_001)")
    export_dataset: bool = Field(True, description="Whether to export CSV and JSON manifest snapshots to disk")
    force_refresh: bool = Field(False, description="Whether to recalculate existing feedback observations")

    model_config = ConfigDict(extra="ignore")


class GenerateFeedbackResponse(BaseModel):
    """Response summary from feedback generation run."""
    processed_count: int = Field(..., description="Total prediction-outcome pairs examined")
    eligible_count: int = Field(..., description="Observations qualified as ELIGIBLE")
    pending_count: int = Field(..., description="Observations categorized as PENDING_OUTCOME")
    excluded_count: int = Field(..., description="Observations categorized as EXCLUDED")
    updated_count: int = Field(..., description="Existing records updated with new outcome actuals")
    dataset_version: Optional[str] = Field(None, description="Assigned dataset version")
    manifest_path: Optional[str] = Field(None, description="File path to generated dataset manifest")
    export_path: Optional[str] = Field(None, description="File path to generated CSV dataset export")
    message: str = Field(..., description="Execution summary status message")

    model_config = ConfigDict(extra="ignore")


class EvaluateModelRequest(BaseModel):
    """Request payload to evaluate a specific model version on feedback records."""
    model_version: str = Field(..., description="Model version string to evaluate (e.g. v1.0.0 or v1.0)")
    dataset_version: Optional[str] = Field(None, description="Optional filter to a specific dataset version")
    min_sample_threshold: int = Field(10, description="Minimum sample size for non-preliminary evaluation")

    model_config = ConfigDict(extra="ignore")


class EvaluateModelResponse(BaseModel):
    """Comprehensive evaluation metrics for a model version against verified feedback."""
    model_version: str = Field(..., description="Evaluated model version")
    dataset_version: Optional[str] = Field(None, description="Evaluated dataset version snapshot")
    status: Literal["EVALUATED", "INSUFFICIENT_DATA"] = Field(..., description="Evaluation outcome status")
    evaluated_count: int = Field(..., description="Number of eligible observations evaluated")
    mae: Optional[float] = Field(None, description="Mean Absolute Error in days")
    rmse: Optional[float] = Field(None, description="Root Mean Squared Error in days")
    mean_signed_error: Optional[float] = Field(None, description="Mean Signed Error (actual - predicted) in days")
    median_absolute_error: Optional[float] = Field(None, description="Median Absolute Error in days")
    min_error: Optional[float] = Field(None, description="Minimum signed prediction error")
    max_error: Optional[float] = Field(None, description="Maximum signed prediction error")
    is_preliminary: bool = Field(False, description="True if sample size is below minimum threshold")
    warnings: List[str] = Field(default_factory=list, description="Data quality, sample size, or bias warnings")
    interpretation: str = Field(..., description="Human-readable assessment of model performance")
    error_sign_convention: str = Field(
        "prediction_error = actual_delay - predicted_delay (positive = delay was underestimated / arrived later than forecast)",
        description="Formal sign convention definition"
    )
    evaluation_timestamp: datetime = Field(..., description="Timestamp when evaluation was executed")

    model_config = ConfigDict(extra="ignore")


class FeedbackDatasetManifest(BaseModel):
    """Versioned feedback dataset manifest metadata."""
    dataset_version: str = Field(..., description="Unique dataset version identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    schema_version: str = Field("1.0", description="Manifest schema version")
    row_count: int = Field(..., description="Total records included in snapshot")
    eligible_count: int = Field(..., description="Eligible records count")
    excluded_count: int = Field(..., description="Excluded records count")
    pending_count: int = Field(..., description="Pending records count")
    model_versions: List[str] = Field(default_factory=list, description="Model versions represented in dataset")
    source_predictions: List[str] = Field(default_factory=list, description="List of included prediction IDs")
    eligibility_rules: List[str] = Field(default_factory=list, description="Applied eligibility rules")
    metrics_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary error metrics of eligible slice")
    checksum: str = Field(..., description="SHA-256 integrity hash of exported dataset")

    model_config = ConfigDict(extra="ignore")
