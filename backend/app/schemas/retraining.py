"""SupplyPrescript — Retraining Schemas (Day 23)
=============================================
Pydantic v2 schemas for automated retraining job management, model performance monitoring,
candidate acceptance reports, promotion approvals, and rollback requests.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

RetrainingStatusType = Literal[
    "QUEUED",
    "RUNNING",
    "EVALUATING",
    "REGISTERED",
    "PROMOTED",
    "REJECTED",
    "FAILED",
    "INSUFFICIENT_DATA",
    "CANCELLED",
]


class RetrainingJobResponse(BaseModel):
    """Schema for a single retraining job record."""
    id: int
    job_id: str = Field(..., description="Unique job execution identifier")
    trigger_reason: str = Field(..., description="Trigger rationale (degradation metric or manual)")
    triggered_by: str = Field("system_pipeline", description="Originating agent or system trigger")
    model_name: str = Field("supplyprescript_delay_engine", description="Target model name")
    parent_model_version: str = Field(..., description="Baseline model version before retraining")
    candidate_model_version: Optional[str] = Field(None, description="Trained candidate model version")
    dataset_version: Optional[str] = Field(None, description="Dataset version or fingerprint used")
    status: RetrainingStatusType = Field(..., description="Current job execution lifecycle status")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    baseline_metrics: Optional[Dict[str, Any]] = None
    candidate_metrics: Optional[Dict[str, Any]] = None
    acceptance_result: Optional[Dict[str, Any]] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class RetrainingJobListResponse(BaseModel):
    """Paginated collection of retraining jobs."""
    items: List[RetrainingJobResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(extra="ignore")


class RunRetrainingRequest(BaseModel):
    """Request payload to initiate or evaluate a retraining cycle."""
    trigger_reason: Optional[str] = Field("Manual operator trigger", description="Reason for initiating run")
    force: bool = Field(False, description="If True, bypasses health check to force candidate training")

    model_config = ConfigDict(extra="ignore")


class RunRetrainingResponse(BaseModel):
    """Execution summary response from a retraining run request."""
    job_id: Optional[str] = None
    status: str
    message: str
    candidate_version: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class PromoteCandidateResponse(BaseModel):
    """Response returned upon promoting a candidate version to production."""
    status: str
    job_id: str
    promoted_version: str
    active_model_version: str
    promoted_at: str

    model_config = ConfigDict(extra="ignore")


class RollbackModelRequest(BaseModel):
    """Request payload to roll back production to a prior registered version."""
    target_version: str = Field(..., description="Target registered version (e.g. 'v1.0')")

    model_config = ConfigDict(extra="ignore")


class RollbackModelResponse(BaseModel):
    """Response returned upon rolling back production model."""
    status: str
    rolled_back_from: str
    active_version: str
    timestamp: str

    model_config = ConfigDict(extra="ignore")


class ModelMonitorStatusResponse(BaseModel):
    """Current performance drift and degradation diagnostic report."""
    status: Literal["DEGRADED", "HEALTHY", "INSUFFICIENT_DATA"]
    is_degraded: bool
    model_version: str
    dataset_version: Optional[str] = None
    evaluated_sample_count: int
    min_sample_threshold: int
    trigger_reason: str
    triggering_metrics: List[str] = Field(default_factory=list)
    current_metrics: Dict[str, Any] = Field(default_factory=dict)
    baseline_metrics: Dict[str, Any] = Field(default_factory=dict)
    thresholds_applied: Dict[str, Any] = Field(default_factory=dict)
    evaluation_timestamp: str

    model_config = ConfigDict(extra="ignore")
