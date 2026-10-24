"""SupplyPrescript — Model Retraining API Router (Day 23)
======================================================
FastAPI endpoints for:
1. POST /api/ml/retraining/run: Evaluates degradation and enqueues candidate retraining.
2. GET /api/ml/retraining/jobs: Lists retraining jobs with status filtering and pagination.
3. GET /api/ml/retraining/jobs/{job_id}: Retrieves specific job details and validation results.
4. POST /api/ml/retraining/jobs/{job_id}/promote: Promotes an approved REGISTERED candidate.
5. POST /api/ml/retraining/rollback: Restores a previous production model version.
6. GET /api/ml/retraining/monitor: Returns live drift and degradation diagnostic metrics.
"""

from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.auth import Role, get_current_user
from app.models.user import User
from app.database.connection import get_db
from app.models.retraining_job import RetrainingJob
from app.schemas.retraining import (
    ModelMonitorStatusResponse,
    PromoteCandidateResponse,
    RetrainingJobListResponse,
    RetrainingJobResponse,
    RollbackModelRequest,
    RollbackModelResponse,
    RunRetrainingRequest,
    RunRetrainingResponse,
)
from app.services.model_monitor import detect_performance_degradation
from app.services.retraining_service import (
    check_retraining_concurrency_and_cooldown,
    enqueue_and_execute_retraining,
    promote_registered_candidate,
    rollback_production_model,
)

logger = logging.getLogger("app.api.routes.retraining")

router = APIRouter(prefix="/api/ml/retraining", tags=["Model Retraining"])


@router.get(
    "/monitor",
    response_model=ModelMonitorStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check Model Performance & Drift Diagnostics (Day 23)",
    description="Evaluates active model against eligible feedback observations and reports performance degradation.",
)
def get_monitor_status(
    model_version: Optional[str] = Query(None, description="Optional target model version"),
    dataset_version: Optional[str] = Query(None, description="Optional dataset version filter"),
    db: Session = Depends(get_db),
) -> ModelMonitorStatusResponse:
    report = detect_performance_degradation(
        db=db,
        model_version=model_version,
        dataset_version=dataset_version,
    )
    return ModelMonitorStatusResponse(**report)


@router.post(
    "/run",
    response_model=RunRetrainingResponse,
    status_code=status.HTTP_200_OK,
    summary="Request Model Retraining Run (Day 23)",
    description="Checks performance degradation, evaluates data availability, and initiates candidate retraining if warranted.",
)
def run_retraining(
    payload: RunRetrainingRequest = RunRetrainingRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunRetrainingResponse:
    if current_user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' lacks permission to trigger retraining. Administrator role required.",
        )
    # 1. Concurrency and cooldown check
    can_proceed, block_reason = check_retraining_concurrency_and_cooldown(db)
    if not can_proceed and not payload.force:
        return RunRetrainingResponse(
            status="BLOCKED",
            message=block_reason or "Retraining blocked due to concurrency or cooldown limits.",
            candidate_version=None,
        )

    # 2. Check degradation unless force=True
    if not payload.force:
        report = detect_performance_degradation(db=db)
        if report["status"] == "INSUFFICIENT_DATA":
            return RunRetrainingResponse(
                status="INSUFFICIENT_DATA",
                message=report["trigger_reason"],
                candidate_version=None,
            )
        if not report["is_degraded"]:
            return RunRetrainingResponse(
                status="HEALTHY",
                message="Model performance is healthy; retraining not needed. Set force=True to override.",
                candidate_version=None,
            )
        trigger_reason = report["trigger_reason"]
        baseline_metrics = report.get("current_metrics")
    else:
        trigger_reason = f"FORCE_OVERRIDE: {payload.trigger_reason}"
        baseline_metrics = None

    # 3. Enqueue and execute
    job = enqueue_and_execute_retraining(
        db=db,
        trigger_reason=trigger_reason,
        triggered_by=current_user.username if current_user else "admin_manual",
        baseline_metrics=baseline_metrics,
        force=payload.force,
    )

    return RunRetrainingResponse(
        job_id=job.job_id,
        status=job.status,
        message=f"Retraining job {job.job_id} completed with status: {job.status}",
        candidate_version=job.candidate_model_version,
    )


@router.get(
    "/jobs",
    response_model=RetrainingJobListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Retraining Jobs (Day 23)",
    description="Retrieve paginated list of retraining jobs with optional status filter.",
)
def list_retraining_jobs(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by job status"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> RetrainingJobListResponse:
    query = db.query(RetrainingJob)
    if status_filter:
        query = query.filter(RetrainingJob.status == status_filter.upper())

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size

    items = query.order_by(desc(RetrainingJob.created_at)).offset(offset).limit(page_size).all()

    return RetrainingJobListResponse(
        items=[RetrainingJobResponse.model_validate(it) for it in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=RetrainingJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Retraining Job Details (Day 23)",
    description="Retrieve execution details, candidate metrics, and validation acceptance report for a specific job.",
)
def get_retraining_job(
    job_id: str,
    db: Session = Depends(get_db),
) -> RetrainingJobResponse:
    job = db.query(RetrainingJob).filter(RetrainingJob.job_id == job_id.strip()).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Retraining job with ID '{job_id}' not found.",
        )
    return RetrainingJobResponse.model_validate(job)


@router.post(
    "/jobs/{job_id}/promote",
    response_model=PromoteCandidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Promote Registered Candidate Model (Day 23)",
    description="Promotes an approved, REGISTERED candidate model version to active production.",
)
def promote_candidate(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PromoteCandidateResponse:
    if current_user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' lacks permission to promote candidate models. Administrator role required.",
        )
    try:
        res = promote_registered_candidate(job_id=job_id.strip(), db=db)
        return PromoteCandidateResponse(**res)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/rollback",
    response_model=RollbackModelResponse,
    status_code=status.HTTP_200_OK,
    summary="Roll Back Active Production Model (Day 23)",
    description="Reverts the active production model to a verified prior registered version.",
)
def rollback_model(
    payload: RollbackModelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RollbackModelResponse:
    if current_user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' lacks permission to roll back production model. Administrator role required.",
        )
    try:
        res = rollback_production_model(target_version=payload.target_version.strip(), db=db)
        return RollbackModelResponse(**res)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
