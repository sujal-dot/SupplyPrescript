"""SupplyPrescript — Retraining Pipeline Service (Day 23)
======================================================
Orchestrates automated and event-driven model retraining workflows, performance monitoring triggers,
candidate training, independent validation, atomic model registry versioning, safe promotion, and rollback.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import pandas as pd
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.feedback import Feedback
from app.models.model_version import ModelVersion
from app.models.prediction import Prediction
from app.models.retraining_job import RetrainingJob
from app.models.shipment import Shipment
from app.services.model_monitor import detect_performance_degradation
from ml.candidate_validation import validate_candidate_model
from ml.feature_config import APPROVED_FEATURES
from ml.model_registry import (
    get_active_model_version,
    get_version_dir,
    promote_model_to_active,
    register_model_version,
    verify_model_artifacts,
)
from ml.predict import reload_active_model
from ml.retrain import (
    CANDIDATES_ROOT_DIR,
    get_next_candidate_version,
    prepare_retraining_dataset,
    train_candidate_models,
)

logger = logging.getLogger("app.services.retraining_service")


def get_recent_feedback_dataframe(db: Session, limit: int = 500) -> pd.DataFrame:
    """Extract eligible verified feedback observations and matched shipment features into a pandas DataFrame."""
    feedbacks = (
        db.query(Feedback)
        .filter(
            Feedback.feedback_status == "ELIGIBLE",
            Feedback.actual_delay.isnot(None),
            Feedback.prediction_error.isnot(None),
        )
        .order_by(Feedback.created_at.desc())
        .limit(limit)
        .all()
    )

    if not feedbacks:
        return pd.DataFrame()

    records = []
    for fb in feedbacks:
        # Resolve shipment features if shipment_id is present
        shipment = None
        if fb.shipment_id:
            shipment = db.query(Shipment).filter(Shipment.shipment_id == fb.shipment_id).first()

        row: Dict[str, Any] = {
            "delay_days": float(fb.actual_delay),
            "delayed": int(float(fb.actual_delay) > 0.0),
        }

        if shipment:
            row.update({
                "supplier_reliability": float(shipment.supplier.supplier_reliability) if shipment.supplier and shipment.supplier.supplier_reliability is not None else 0.85,
                "historical_avg_delay": float(shipment.delay_days) if shipment.delay_days is not None else 0.0,
                "lead_time": int(shipment.lead_time) if shipment.lead_time is not None else 7,
                "inventory_level": 500,
                "demand": int(shipment.quantity) if shipment.quantity is not None else 100,
                "quantity": int(shipment.quantity) if shipment.quantity is not None else 100,
                "shipping_cost": float(shipment.shipping_cost) if shipment.shipping_cost is not None else 150.0,
                "distance": float(shipment.distance) if hasattr(shipment, "distance") and shipment.distance else 500.0,
                "transport_mode": shipment.transport_mode or "Road",
                "season": "Winter",
                "priority": shipment.priority or "High",
            })
        else:
            # Fallback neutral features adhering to schema
            row.update({
                "supplier_reliability": 0.85,
                "historical_avg_delay": 0.0,
                "lead_time": 7,
                "inventory_level": 500,
                "demand": 100,
                "quantity": 100,
                "shipping_cost": 150.0,
                "distance": 500.0,
                "transport_mode": "Road",
                "season": "Winter",
                "priority": "High",
            })

        records.append(row)

    return pd.DataFrame(records)


def check_retraining_concurrency_and_cooldown(db: Session) -> Tuple[bool, Optional[str]]:
    """Verify that concurrent jobs limit and cooldown period are respected.

    Returns:
        (can_proceed: bool, reason: Optional[str])
    """
    # 1. Concurrency check
    running_jobs = (
        db.query(RetrainingJob)
        .filter(RetrainingJob.status.in_(["QUEUED", "RUNNING", "EVALUATING"]))
        .count()
    )
    if running_jobs >= settings.RETRAINING_MAX_CONCURRENT_JOBS:
        return False, f"Maximum concurrent retraining jobs ({settings.RETRAINING_MAX_CONCURRENT_JOBS}) reached."

    # 2. Cooldown check
    cooldown_cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.RETRAINING_COOLDOWN_MINUTES)
    last_job = (
        db.query(RetrainingJob)
        .filter(RetrainingJob.status.in_(["RUNNING", "REGISTERED", "PROMOTED"]))
        .order_by(desc(RetrainingJob.created_at))
        .first()
    )
    if last_job and last_job.created_at:
        # Check tz-awareness
        job_time = last_job.created_at
        if job_time.tzinfo is None:
            job_time = job_time.replace(tzinfo=timezone.utc)
        if job_time > cooldown_cutoff:
            mins_left = int((job_time - cooldown_cutoff).total_seconds() / 60)
            return False, f"Retraining in cooldown period. Try again in {mins_left} minutes."

    return True, None


def trigger_feedback_monitoring_cycle(db: Session, triggered_by: str = "feedback_pipeline") -> Dict[str, Any]:
    """Execute continuous learning trigger workflow when new feedback actuals are processed."""
    active_v = get_active_model_version()
    report = detect_performance_degradation(db, model_version=active_v)

    if report["status"] == "INSUFFICIENT_DATA":
        logger.info("Feedback monitoring cycle: %s", report["trigger_reason"])
        return {
            "status": "INSUFFICIENT_DATA",
            "action_taken": "NONE",
            "message": report["trigger_reason"],
            "report": report,
        }

    if not report["is_degraded"]:
        logger.info("Feedback monitoring cycle: Model %s is healthy. No retraining needed.", active_v)
        return {
            "status": "HEALTHY",
            "action_taken": "NONE",
            "message": f"Model {active_v} is performing within acceptable tolerance.",
            "report": report,
        }

    # Model is degraded — check concurrency & cooldown
    can_run, reason = check_retraining_concurrency_and_cooldown(db)
    if not can_run:
        logger.warning("Degradation detected but retraining deferred: %s", reason)
        return {
            "status": "DEFERRED",
            "action_taken": "NONE",
            "message": reason,
            "report": report,
        }

    # Enqueue and execute retraining
    logger.info("Degradation detected for model %s. Triggering candidate retraining...", active_v)
    job = enqueue_and_execute_retraining(
        db=db,
        trigger_reason=report["trigger_reason"],
        triggered_by=triggered_by,
        baseline_metrics=report.get("current_metrics"),
    )

    return {
        "status": "RETRAINING_TRIGGERED",
        "action_taken": "JOB_ENQUEUED",
        "job_id": job.job_id,
        "job_status": job.status,
        "message": f"Retraining job {job.job_id} initiated due to detected degradation.",
        "report": report,
    }


def enqueue_and_execute_retraining(
    db: Session,
    trigger_reason: str,
    triggered_by: str = "operator_manual",
    baseline_metrics: Optional[Dict[str, Any]] = None,
    force: bool = False,
) -> RetrainingJob:
    """Create a retraining job and execute the candidate training and validation pipeline."""
    active_v = get_active_model_version()
    job_id = f"RETRAIN_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{uuid.uuid4().hex[:6].upper()}"

    job = RetrainingJob(
        job_id=job_id,
        trigger_reason=trigger_reason,
        triggered_by=triggered_by,
        model_name="supplyprescript_delay_engine",
        parent_model_version=active_v,
        status="RUNNING",
        started_at=datetime.now(timezone.utc),
        baseline_metrics=baseline_metrics,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        # 1. Fetch eligible feedback records
        feedback_df = get_recent_feedback_dataframe(db)

        # 2. Prepare combined training dataset
        train_df, val_df, test_df, fingerprint = prepare_retraining_dataset(feedback_df)
        job.dataset_version = f"FINGERPRINT_{fingerprint[:12]}"

        # 3. Allocate candidate version
        candidate_version = get_next_candidate_version(active_v)
        job.candidate_model_version = candidate_version
        db.commit()

        # 4. Train candidate models in isolated directory
        candidate_dir = CANDIDATES_ROOT_DIR / candidate_version
        train_result = train_candidate_models(
            train_df=train_df,
            val_df=val_df,
            test_df=test_df,
            candidate_version=candidate_version,
            output_dir=candidate_dir,
        )

        job.status = "EVALUATING"
        db.commit()

        # 5. Independent validation and acceptance comparison
        val_result = validate_candidate_model(
            candidate_version=candidate_version,
            candidate_dir=candidate_dir,
            baseline_version=active_v,
            evaluation_df=test_df,
            min_improvement_pct=settings.RETRAINING_MIN_IMPROVEMENT_PCT,
            max_secondary_regression_pct=settings.RETRAINING_MAX_SECONDARY_REGRESSION_PCT,
        )

        job.candidate_metrics = val_result.get("comparison", {})
        job.acceptance_result = val_result

        # 6. Promotion or Registration Decision
        if val_result.get("accepted"):
            logger.info("Candidate version %s passed all acceptance criteria!", candidate_version)

            # Register version in production registry
            cand_clf = joblib.load(candidate_dir / "classifier.pkl")
            cand_reg = joblib.load(candidate_dir / "regressor.pkl")
            cand_prep = joblib.load(candidate_dir / "preprocessor.pkl")
            with open(candidate_dir / "metadata.json", "r", encoding="utf-8") as f:
                cand_meta = json.load(f)
            with open(candidate_dir / "metrics.json", "r", encoding="utf-8") as f:
                cand_mets = json.load(f)

            register_model_version(
                version=candidate_version,
                classifier=cand_clf,
                regressor=cand_reg,
                preprocessor=cand_prep,
                metadata=cand_meta,
                metrics=cand_mets,
                overwrite=True,
                set_active=False,
            )

            # Record in PostgreSQL model_versions table
            db_mv = (
                db.query(ModelVersion)
                .filter(ModelVersion.version == candidate_version)
                .first()
            )
            if not db_mv:
                db_mv = ModelVersion(
                    model_name="delay_risk_classifier",
                    version=candidate_version,
                    model_type="XGBoost Dual Engine",
                    algorithm="XGBClassifier + XGBRegressor",
                    training_date=datetime.now(timezone.utc),
                    dataset_version=job.dataset_version,
                    metrics=val_result.get("candidate_metrics"),
                    model_path=str(get_version_dir(candidate_version)),
                    is_active=False,
                )
                db.add(db_mv)
                db.commit()

            if settings.RETRAINING_AUTO_PROMOTION_ENABLED:
                logger.info("Auto-promotion enabled: promoting %s to active production", candidate_version)
                promote_model_to_active(candidate_version)
                db.query(ModelVersion).filter(ModelVersion.version != candidate_version).update({"is_active": False})
                db_mv.is_active = True
                db.commit()
                reload_active_model()
                job.status = "PROMOTED"
            else:
                logger.info("Candidate %s REGISTERED; awaiting explicit approval for promotion", candidate_version)
                job.status = "REGISTERED"

        else:
            logger.warning("Candidate %s rejected: failed acceptance checks (%s)", candidate_version, val_result.get("errors"))
            job.status = "REJECTED"
            job.failure_reason = "; ".join(val_result.get("errors", []))

    except Exception as e:
        logger.error("Retraining job %s failed with exception: %s", job_id, e, exc_info=True)
        job.status = "FAILED"
        job.failure_reason = str(e)

    finally:
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)

    return job


def promote_registered_candidate(job_id: str, db: Session) -> Dict[str, Any]:
    """Promote an accepted and REGISTERED candidate model version to active production status."""
    job = db.query(RetrainingJob).filter(RetrainingJob.job_id == job_id).first()
    if not job:
        raise ValueError(f"Retraining job with ID '{job_id}' not found.")

    if job.status not in ["REGISTERED", "PROMOTED"]:
        raise ValueError(
            f"Cannot promote job '{job_id}': status is '{job.status}'. Only REGISTERED candidates can be promoted."
        )

    cand_v = job.candidate_model_version
    if not cand_v:
        raise ValueError(f"Job '{job_id}' has no candidate_model_version assigned.")

    # Re-verify candidate artifacts before promotion
    verification = verify_model_artifacts(cand_v)
    if not verification["valid"]:
        raise ValueError(f"Promotion rejected: artifact verification failed: {verification['errors']}")

    # Promote atomically
    promote_model_to_active(cand_v)

    # Update database model_versions table
    db.query(ModelVersion).filter(ModelVersion.version != cand_v).update({"is_active": False})
    cand_db = db.query(ModelVersion).filter(ModelVersion.version == cand_v).first()
    if cand_db:
        cand_db.is_active = True
    else:
        new_mv = ModelVersion(
            model_name="delay_risk_classifier",
            version=cand_v,
            model_type="XGBoost Dual Engine",
            algorithm="XGBClassifier + XGBRegressor",
            training_date=datetime.now(timezone.utc),
            dataset_version=job.dataset_version,
            metrics=job.candidate_metrics,
            model_path=str(get_version_dir(cand_v)),
            is_active=True,
        )
        db.add(new_mv)

    # Reload active inference bundle in memory
    reloaded_version = reload_active_model()

    job.status = "PROMOTED"
    job.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info("Successfully promoted candidate version '%s' to active production!", cand_v)
    return {
        "status": "SUCCESS",
        "job_id": job.job_id,
        "promoted_version": cand_v,
        "active_model_version": reloaded_version,
        "promoted_at": datetime.now(timezone.utc).isoformat(),
    }


def rollback_production_model(target_version: str, db: Session) -> Dict[str, Any]:
    """Roll back active production model to a verified prior registered version."""
    v_clean = target_version.strip()
    v_dir = get_version_dir(v_clean)

    if not v_dir.exists():
        raise FileNotFoundError(f"Model version '{v_clean}' does not exist in registry.")

    verification = verify_model_artifacts(v_clean)
    if not verification["valid"]:
        raise ValueError(f"Cannot rollback to '{v_clean}': verification failed: {verification['errors']}")

    previous_active = get_active_model_version()
    promote_model_to_active(v_clean)

    # Update database model_versions
    db.query(ModelVersion).filter(ModelVersion.version != v_clean).update({"is_active": False})
    target_db = db.query(ModelVersion).filter(ModelVersion.version == v_clean).first()
    if target_db:
        target_db.is_active = True
    db.commit()

    reloaded_version = reload_active_model()
    logger.info("Rolled back active production model from '%s' to '%s'", previous_active, reloaded_version)

    return {
        "status": "SUCCESS",
        "rolled_back_from": previous_active,
        "active_version": reloaded_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
