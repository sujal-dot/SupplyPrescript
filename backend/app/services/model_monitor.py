"""SupplyPrescript — Model Performance Monitoring & Degradation Detection Service (Day 23)
========================================================================================
Continuously monitors production ML model performance against ground-truth feedback outcomes,
detects distribution shift and performance degradation, applies configurable threshold rules,
and provides structured diagnostic reports for automatic retraining triggers.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.feedback import Feedback
from app.services.prediction_feedback import evaluate_model_on_feedback
from ml.model_registry import (
    get_active_model_version,
    get_version_dir,
    MODEL_VERSIONS_DIR,
)

logger = logging.getLogger("app.services.model_monitor")


def load_model_baseline_metrics(model_version: str) -> Dict[str, Any]:
    """Retrieve recorded baseline metrics for a model version from models/versions/{version}/metrics.json."""
    v_clean = model_version.strip()
    # Normalize version string
    v_dir = get_version_dir(v_clean)
    metrics_file = v_dir / "metrics.json"

    if not metrics_file.exists():
        # Fallback search if directory name lacks or has extra 'v'
        alt_name = v_clean.lower() if v_clean.startswith("v") else f"v{v_clean.lower()}"
        alt_file = MODEL_VERSIONS_DIR / alt_name / "metrics.json"
        if alt_file.exists():
            metrics_file = alt_file

    if metrics_file.exists():
        try:
            with open(metrics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.warning("Could not read baseline metrics from %s: %s", metrics_file, e)

    # Return provisional default baseline if metrics file not available
    logger.info("Using default baseline metrics for model version '%s'", model_version)
    return {
        "regression": {
            "mae": 2.0369,
            "rmse": 2.9089,
            "median_absolute_error": 1.7822,
            "sample_count": 2250,
        },
        "classification": {
            "f1_score": 0.3785,
            "precision": 0.2409,
            "recall": 0.8834,
            "roc_auc": 0.5822,
            "sample_count": 2250,
        },
    }


def detect_performance_degradation(
    db: Session,
    model_version: Optional[str] = None,
    dataset_version: Optional[str] = None,
    min_feedback_threshold: Optional[int] = None,
    mae_threshold_pct: Optional[float] = None,
    mae_absolute_days: Optional[float] = None,
) -> Dict[str, Any]:
    """Evaluate whether model performance has degraded beyond configured thresholds.

    Workflow:
    1. Resolve target model version (defaults to active production version).
    2. Check count of verified ELIGIBLE feedback records.
    3. If sample size < min_feedback_threshold, return INSUFFICIENT_DATA.
    4. Compute live evaluation metrics on eligible feedback actuals.
    5. Compare against recorded baseline metrics for that model version.
    6. Evaluate directional error metrics (higher MAE/RMSE = degraded).
    7. Return comprehensive diagnostic report with triggering rationale.

    Args:
        db: SQLAlchemy database session.
        model_version: Target model version string (e.g. 'v1.0' or 'v1.0.0').
        dataset_version: Optional feedback dataset version snapshot filter.
        min_feedback_threshold: Minimum sample size required for evaluation.
        mae_threshold_pct: Relative MAE degradation percentage threshold (default: 15.0%).
        mae_absolute_days: Absolute MAE degradation days threshold (default: 0.25 days).

    Returns:
        Dict adhering to monitoring diagnostic report schema.
    """
    active_v = get_active_model_version()
    target_version = model_version or active_v
    min_samples = min_feedback_threshold or settings.RETRAINING_MIN_FEEDBACK_THRESHOLD
    threshold_pct = mae_threshold_pct if mae_threshold_pct is not None else settings.RETRAINING_DEGRADATION_MAE_THRESHOLD_PCT
    abs_days_threshold = mae_absolute_days if mae_absolute_days is not None else settings.RETRAINING_DEGRADATION_MAE_ABSOLUTE_DAYS

    now_utc = datetime.now(timezone.utc).isoformat()

    # Query eligible feedback records count
    query = db.query(Feedback).filter(
        Feedback.feedback_status == "ELIGIBLE",
        Feedback.actual_delay.isnot(None),
        Feedback.prediction_error.isnot(None),
    )
    if target_version:
        # Match flexible version format (v1.0 or v1.0.0)
        norm_v = target_version.strip()
        query = query.filter(
            (Feedback.model_version == norm_v)
            | (Feedback.model_version == f"{norm_v}.0")
            | (Feedback.model_version == norm_v.rstrip(".0"))
        )
    if dataset_version:
        query = query.filter(Feedback.dataset_version == dataset_version)

    eligible_count = query.count()

    baseline_data = load_model_baseline_metrics(target_version)
    reg_baseline = baseline_data.get("regression", {})
    base_mae = reg_baseline.get("mae", 2.0369)
    base_rmse = reg_baseline.get("rmse", 2.9089)

    # 1. Check minimum sample requirement
    if eligible_count < min_samples:
        return {
            "status": "INSUFFICIENT_DATA",
            "is_degraded": False,
            "trigger_retraining": False,
            "model_version": target_version,
            "dataset_version": dataset_version,
            "evaluated_sample_count": eligible_count,
            "min_sample_threshold": min_samples,
            "trigger_reason": (
                f"INSUFFICIENT_DATA: {eligible_count} verified eligible feedback observations "
                f"available; minimum threshold is {min_samples}. Retraining deferred."
            ),
            "triggering_metrics": [],
            "current_metrics": {
                "sample_count": eligible_count,
                "mae": None,
                "rmse": None,
                "mean_signed_error": None,
            },
            "baseline_metrics": {
                "mae": base_mae,
                "rmse": base_rmse,
                "sample_count": reg_baseline.get("sample_count", 2250),
            },
            "thresholds_applied": {
                "min_sample_threshold": min_samples,
                "degradation_mae_threshold_pct": threshold_pct,
                "degradation_mae_absolute_days": abs_days_threshold,
            },
            "evaluation_timestamp": now_utc,
        }

    # 2. Evaluate current model on feedback
    eval_result = evaluate_model_on_feedback(
        db=db,
        model_version=target_version,
        dataset_version=dataset_version,
        min_sample_threshold=min_samples,
    )

    current_mae = eval_result.get("mae")
    current_rmse = eval_result.get("rmse")
    current_bias = eval_result.get("mean_signed_error")
    current_median_ae = eval_result.get("median_absolute_error")

    if current_mae is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "is_degraded": False,
            "trigger_retraining": False,
            "model_version": target_version,
            "dataset_version": dataset_version,
            "evaluated_sample_count": eligible_count,
            "min_sample_threshold": min_samples,
            "trigger_reason": "INSUFFICIENT_DATA: Live evaluation returned no computed error metrics.",
            "triggering_metrics": [],
            "current_metrics": {"sample_count": eligible_count},
            "baseline_metrics": {"mae": base_mae, "rmse": base_rmse},
            "thresholds_applied": {
                "min_sample_threshold": min_samples,
                "degradation_mae_threshold_pct": threshold_pct,
                "degradation_mae_absolute_days": abs_days_threshold,
            },
            "evaluation_timestamp": now_utc,
        }

    # 3. Compute degradation deltas
    # Higher MAE/RMSE indicates worse performance
    mae_diff = round(current_mae - base_mae, 4)
    mae_pct_change = round(((current_mae - base_mae) / base_mae) * 100.0, 2) if base_mae > 0 else 0.0

    rmse_diff = round(current_rmse - base_rmse, 4) if current_rmse is not None else 0.0
    rmse_pct_change = round(((current_rmse - base_rmse) / base_rmse) * 100.0, 2) if base_rmse > 0 and current_rmse else 0.0

    triggering_metrics: List[str] = []
    is_degraded = False

    # Check relative MAE degradation
    if mae_pct_change >= threshold_pct:
        is_degraded = True
        triggering_metrics.append(
            f"MAE increased by {mae_pct_change:+.1f}% (current: {current_mae:.2f}d vs baseline: {base_mae:.2f}d; threshold: >= {threshold_pct}%)"
        )

    # Check absolute MAE degradation
    if mae_diff >= abs_days_threshold:
        is_degraded = True
        triggering_metrics.append(
            f"Absolute MAE miss worsened by {mae_diff:+.2f} days (threshold: >= {abs_days_threshold} days)"
        )

    # Check secondary metric: severe RMSE regression (>25% increase)
    if rmse_pct_change >= 25.0:
        is_degraded = True
        triggering_metrics.append(
            f"RMSE increased significantly by {rmse_pct_change:+.1f}% (current: {current_rmse:.2f}d vs baseline: {base_rmse:.2f}d)"
        )

    # Check severe directional bias drift (|bias| >= 1.5 days)
    if current_bias is not None and abs(current_bias) >= 1.5:
        is_degraded = True
        triggering_metrics.append(
            f"Severe directional bias drift: Mean Signed Error = {current_bias:+.2f} days (systematic miss)"
        )

    status_str = "DEGRADED" if is_degraded else "HEALTHY"
    trigger_reason = (
        f"PERFORMANCE_DEGRADATION: {'; '.join(triggering_metrics)}"
        if is_degraded
        else f"HEALTHY: Current MAE {current_mae:.2f}d within configured tolerance of baseline {base_mae:.2f}d."
    )

    return {
        "status": status_str,
        "is_degraded": is_degraded,
        "trigger_retraining": is_degraded,
        "model_version": target_version,
        "dataset_version": dataset_version,
        "evaluated_sample_count": eligible_count,
        "min_sample_threshold": min_samples,
        "trigger_reason": trigger_reason,
        "triggering_metrics": triggering_metrics,
        "current_metrics": {
            "sample_count": eligible_count,
            "mae": round(current_mae, 4),
            "rmse": round(current_rmse, 4) if current_rmse is not None else None,
            "mean_signed_error": round(current_bias, 4) if current_bias is not None else None,
            "median_absolute_error": round(current_median_ae, 4) if current_median_ae is not None else None,
            "mae_delta": mae_diff,
            "mae_delta_pct": mae_pct_change,
            "rmse_delta": rmse_diff,
            "rmse_delta_pct": rmse_pct_change,
        },
        "baseline_metrics": {
            "mae": round(base_mae, 4),
            "rmse": round(base_rmse, 4),
            "sample_count": reg_baseline.get("sample_count", 2250),
        },
        "thresholds_applied": {
            "min_sample_threshold": min_samples,
            "degradation_mae_threshold_pct": threshold_pct,
            "degradation_mae_absolute_days": abs_days_threshold,
        },
        "evaluation_timestamp": now_utc,
    }
