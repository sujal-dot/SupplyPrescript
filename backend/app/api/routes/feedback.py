"""SupplyPrescript — Model Feedback API Router (Day 22)
===================================================
Endpoints for:
1. POST /api/feedback/generate: Scans predictions & outcomes, validates eligibility, computes errors, persists feedback.
2. GET /api/feedback: Lists feedback records with pagination, filtering, and summary statistics.
3. GET /api/feedback/{feedback_id}: Retrieves specific persisted feedback record.
4. POST /api/feedback/evaluate: Evaluates model version accuracy against eligible feedback observations.
5. GET /api/feedback/datasets: Lists available versioned dataset manifests.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path as FastPath, HTTPException, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.auth import Role, get_current_user
from app.models.user import User
from app.database.connection import get_db
from app.models.feedback import Feedback
from app.schemas.feedback import (
    FeedbackItemResponse,
    FeedbackListResponse,
    FeedbackSummaryCounts,
    GenerateFeedbackRequest,
    GenerateFeedbackResponse,
    EvaluateModelRequest,
    EvaluateModelResponse,
)
from app.services.prediction_feedback import (
    generate_feedback_pipeline,
    evaluate_model_on_feedback,
    MANIFESTS_DIR,
)

router = APIRouter(prefix="/api/feedback", tags=["Model Feedback"])


@router.post(
    "/generate",
    response_model=GenerateFeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate or Refresh Feedback Observations (Day 22)",
    description=(
        "Scans stored predictions and matching operational delivery outcomes. Validates eligibility, "
        "calculates prediction errors, updates PostgreSQL feedback records, and deterministically "
        "exports versioned dataset snapshots and manifests. Idempotent."
    ),
)
def generate_feedback_endpoint(
    payload: GenerateFeedbackRequest = GenerateFeedbackRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateFeedbackResponse:
    """POST /api/feedback/generate handler."""
    if current_user.role not in [Role.ANALYST.value, Role.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' lacks permission to generate feedback datasets.",
        )
    result = generate_feedback_pipeline(
        db=db,
        dataset_version=payload.dataset_version,
        export_dataset=payload.export_dataset,
        force_refresh=payload.force_refresh,
    )
    # Event-driven trigger: Check continuous learning monitoring cycle upon new feedback batch
    try:
        from app.services.retraining_service import trigger_feedback_monitoring_cycle
        trigger_feedback_monitoring_cycle(db=db, triggered_by="feedback_generate_api")
    except Exception as e:
        import logging
        logging.getLogger("app.api.routes.feedback").warning("Feedback monitoring trigger warning: %s", e)

    return GenerateFeedbackResponse(**result)


@router.get(
    "",
    response_model=FeedbackListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Feedback Observations (Day 22)",
    description="Retrieve paginated feedback records with filtering and aggregate pipeline status summary.",
)
def list_feedback_endpoint(
    shipment_id: Optional[str] = Query(None, description="Filter by shipment ID"),
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    feedback_status: Optional[str] = Query(None, description="Filter by status (ELIGIBLE, PENDING_OUTCOME, EXCLUDED, UNDER_REVIEW)"),
    dataset_version: Optional[str] = Query(None, description="Filter by dataset version"),
    start_date: Optional[datetime] = Query(None, description="Prediction timestamp on or after"),
    end_date: Optional[datetime] = Query(None, description="Prediction timestamp on or before"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> FeedbackListResponse:
    """GET /api/feedback handler."""
    query = db.query(Feedback)

    if shipment_id:
        query = query.filter(Feedback.shipment_id.ilike(f"%{shipment_id.strip()}%"))

    if model_version:
        query = query.filter(Feedback.model_version.ilike(f"%{model_version.strip()}%"))

    if feedback_status:
        query = query.filter(Feedback.feedback_status == feedback_status.strip().upper())

    if dataset_version:
        query = query.filter(Feedback.dataset_version == dataset_version.strip())

    if start_date:
        query = query.filter(Feedback.prediction_timestamp >= start_date)

    if end_date:
        query = query.filter(Feedback.prediction_timestamp <= end_date)

    total = query.count()

    # Pagination
    items = (
        query.order_by(desc(Feedback.prediction_timestamp), desc(Feedback.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 1

    # Pipeline summary counts across entire filter scope or table
    all_query = db.query(Feedback)
    if shipment_id:
        all_query = all_query.filter(Feedback.shipment_id.ilike(f"%{shipment_id.strip()}%"))
    if model_version:
        all_query = all_query.filter(Feedback.model_version.ilike(f"%{model_version.strip()}%"))

    total_all = all_query.count()
    eligible_cnt = all_query.filter(Feedback.feedback_status == "ELIGIBLE").count()
    pending_cnt = all_query.filter(Feedback.feedback_status == "PENDING_OUTCOME").count()
    excluded_cnt = all_query.filter(Feedback.feedback_status == "EXCLUDED").count()
    review_cnt = all_query.filter(Feedback.feedback_status == "UNDER_REVIEW").count()

    # Overall MAE & bias for eligible records
    eligible_records = (
        all_query.filter(
            Feedback.feedback_status == "ELIGIBLE",
            Feedback.prediction_error.isnot(None),
            Feedback.absolute_error.isnot(None),
        ).all()
    )
    overall_mae = None
    overall_bias = None
    if eligible_records:
        abs_errs = [float(r.absolute_error) for r in eligible_records]
        signed_errs = [float(r.prediction_error) for r in eligible_records]
        overall_mae = round(sum(abs_errs) / len(abs_errs), 2)
        overall_bias = round(sum(signed_errs) / len(signed_errs), 2)

    summary_counts = FeedbackSummaryCounts(
        total=total_all,
        eligible=eligible_cnt,
        pending_outcome=pending_cnt,
        excluded=excluded_cnt,
        under_review=review_cnt,
        mean_absolute_error=overall_mae,
        mean_signed_error=overall_bias,
    )

    return FeedbackListResponse(
        items=[FeedbackItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        summary_counts=summary_counts,
    )


@router.get(
    "/datasets",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Versioned Feedback Datasets",
    description="Lists all saved dataset manifests generated by the feedback pipeline.",
)
def list_dataset_manifests() -> List[Dict[str, Any]]:
    """GET /api/feedback/datasets handler."""
    manifests: List[Dict[str, Any]] = []
    if MANIFESTS_DIR.exists():
        for mf in sorted(MANIFESTS_DIR.glob("*.json"), reverse=True):
            try:
                with open(mf, "r", encoding="utf-8") as f:
                    manifests.append(json.load(f))
            except Exception as e:
                logger.warning("Failed to parse manifest %s: %s", mf, e)
    return manifests


@router.get(
    "/{feedback_id}",
    response_model=FeedbackItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Feedback Record",
    description="Retrieve a single feedback record by business ID or integer ID.",
)
def get_feedback_record_endpoint(
    feedback_id: str = FastPath(..., description="Unique feedback identifier (e.g. FB-XXXXXX)"),
    db: Session = Depends(get_db),
) -> FeedbackItemResponse:
    """GET /api/feedback/{feedback_id} handler."""
    clean_id = feedback_id.strip()
    record = db.query(Feedback).filter(Feedback.feedback_id == clean_id).first()

    if not record and clean_id.isdigit():
        record = db.query(Feedback).filter(Feedback.id == int(clean_id)).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback record '{clean_id}' not found.",
        )

    return FeedbackItemResponse.model_validate(record)


@router.post(
    "/evaluate",
    response_model=EvaluateModelResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Model Accuracy on Feedback (Day 22)",
    description=(
        "Evaluates a specified model version against verified eligible feedback records. "
        "Calculates MAE, RMSE, Mean Signed Error (directional bias), and Median Absolute Error. "
        "Does not train, promote, or replace production models."
    ),
)
def evaluate_model_endpoint(
    payload: EvaluateModelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvaluateModelResponse:
    """POST /api/feedback/evaluate handler."""
    if current_user.role not in [Role.ANALYST.value, Role.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' lacks permission to evaluate models.",
        )
    result = evaluate_model_on_feedback(
        db=db,
        model_version=payload.model_version,
        dataset_version=payload.dataset_version,
        min_sample_threshold=payload.min_sample_threshold,
    )
    return EvaluateModelResponse(**result)
