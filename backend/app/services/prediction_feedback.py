"""SupplyPrescript — Model Feedback Pipeline Service (Day 22)
============================================================
Authoritative backend service for comparing stored delay predictions with actual delivery
outcomes, calculating signed prediction errors, validating feedback eligibility, generating
versioned feedback datasets, and evaluating model performance over time.

Mathematical & Accounting Conventions:
--------------------------------------
1. Prediction Error:
   prediction_error = actual_delay - predicted_delay
   - Positive error: actual delay exceeded prediction (model underestimated delay / arrived late).
   - Negative error: actual delay was lower than predicted (model overestimated delay / arrived early).
   - Zero error: predicted delay matched actual delay.

2. Absolute Error:
   absolute_error = abs(actual_delay - predicted_delay)
   - Guaranteed non-negative.

3. Evaluation Metrics:
   - MAE  = mean(abs(actual_delay - predicted_delay))
   - RMSE = sqrt(mean((actual_delay - predicted_delay) ** 2))
   - Mean Signed Error = mean(actual_delay - predicted_delay)  (Directional Bias)
   - Median Absolute Error = median(abs(actual_delay - predicted_delay))

Data Quality & Eligibility:
---------------------------
- Pending deliveries are categorized as PENDING_OUTCOME and never counted as 0-error or failures.
- Non-negative actual delay constraint is enforced (actual_delay >= 0).
- Model versions must be tracked from original predictions, never inferred from active model.
- Model evaluation endpoint is strictly read-only and does not promote or replace models.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import math
import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.models.prediction import Prediction
from app.models.recommendation import Recommendation
from app.models.decision import Decision
from app.models.outcome import Outcome
from app.models.shipment import Shipment
from app.models.model_version import ModelVersion

logger = logging.getLogger("app.services.prediction_feedback")

FEEDBACK_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "feedback"
MANIFESTS_DIR = FEEDBACK_DATA_DIR / "manifests"
EXPORTS_DIR = FEEDBACK_DATA_DIR / "exports"

DEFAULT_MIN_SAMPLE_THRESHOLD = 10


# ---------------------------------------------------------------------------
# 1. Prediction Error Calculation
# ---------------------------------------------------------------------------
def calculate_prediction_error(
    predicted_delay: Decimal | float | int | str,
    actual_delay: Optional[Decimal | float | int | str],
) -> Dict[str, Optional[float]]:
    """Calculate signed prediction error and absolute error adhering to Day 22 sign convention.

    Formula:
        prediction_error = actual_delay - predicted_delay
        absolute_error   = abs(actual_delay - predicted_delay)

    Args:
        predicted_delay: Stored predicted delay in days.
        actual_delay: Verified actual delay in days, or None if pending.

    Returns:
        Dict with keys 'prediction_error' and 'absolute_error'.

    Raises:
        ValueError: If predicted_delay is None or invalid, or if actual_delay < 0.
    """
    if predicted_delay is None:
        raise ValueError("predicted_delay cannot be None.")

    try:
        p_val = round(float(predicted_delay), 2)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid predicted_delay value: {predicted_delay}") from e

    if actual_delay is None:
        return {"prediction_error": None, "absolute_error": None}

    try:
        a_val = round(float(actual_delay), 2)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid actual_delay value: {actual_delay}") from e

    # Domain rule: actual delivery delay cannot be negative in SupplyPrescript
    if a_val < 0:
        raise ValueError(f"Invalid actual_delay: {a_val}. Actual delay cannot be negative.")

    error = round(a_val - p_val, 2)
    abs_err = round(abs(error), 2)

    return {
        "prediction_error": error,
        "absolute_error": abs_err,
    }


# ---------------------------------------------------------------------------
# 2. Feedback Eligibility Validation
# ---------------------------------------------------------------------------
def validate_feedback_eligibility(
    prediction: Any,
    model_version: Optional[str],
    outcome: Optional[Any],
    decision: Optional[Any] = None,
) -> Tuple[str, Optional[str]]:
    """Evaluate whether a prediction-outcome pair qualifies for the model evaluation dataset.

    Returns:
        (feedback_status, exclusion_reason)
        Status: 'ELIGIBLE' | 'PENDING_OUTCOME' | 'EXCLUDED' | 'UNDER_REVIEW'
    """
    # 1. Original prediction check
    if not prediction:
        return "EXCLUDED", "MISSING_PREDICTION: Original prediction record is missing."

    pred_id = getattr(prediction, "prediction_id", None)
    if not pred_id:
        return "EXCLUDED", "INVALID_PREDICTION_ID: Prediction identifier is missing."

    # 2. Model version check
    if not model_version or not str(model_version).strip():
        return "EXCLUDED", "UNKNOWN_MODEL_VERSION: Original model version was not recorded."

    # 3. Outcome availability check
    if not outcome:
        return "PENDING_OUTCOME", "PENDING_OUTCOME: Operational delivery outcome has not been recorded."

    status = (getattr(outcome, "outcome_status", "") or "").upper()

    # 4. Inconclusive or non-final statuses
    if status in ("AWAITING_DELIVERY", "PENDING", "PENDING_REVIEW"):
        return "PENDING_OUTCOME", f"PENDING_OUTCOME: Shipment awaiting delivery (status: {status})."

    if status == "DISPUTED":
        return "UNDER_REVIEW", "OUTCOME_DISPUTED: Delivery receipt or milestone dates are in dispute."

    if status == "CANCELLED":
        return "EXCLUDED", "SHIPMENT_CANCELLED: Shipment was cancelled prior to operational delivery."

    # 5. Actual delay validity
    raw_act_delay = getattr(outcome, "actual_delay", None)
    if raw_act_delay is None:
        return "PENDING_OUTCOME", "MISSING_ACTUAL_DELAY: Delivery completed but actual delay is unrecorded."

    try:
        act_delay = float(raw_act_delay)
    except (ValueError, TypeError):
        return "EXCLUDED", f"INVALID_ACTUAL_DELAY: Non-numeric delay value: {raw_act_delay}"

    if act_delay < 0:
        return "EXCLUDED", f"INVALID_DELAY_VALUE: Actual delay ({act_delay}) violates non-negative rule."

    # 6. Prediction delay validity
    raw_pred_delay = getattr(decision, "predicted_delay", None) if decision else None
    if raw_pred_delay is None:
        raw_pred_delay = getattr(prediction, "predicted_value", None)

    if raw_pred_delay is None:
        return "EXCLUDED", "MISSING_PREDICTED_DELAY: Stored predicted delay is null."

    try:
        pred_delay = float(raw_pred_delay)
    except (ValueError, TypeError):
        return "EXCLUDED", f"INVALID_PREDICTED_DELAY: Non-numeric predicted delay: {raw_pred_delay}"

    # All criteria satisfied
    return "ELIGIBLE", None


# ---------------------------------------------------------------------------
# 3. Generate or Refresh Feedback Dataset
# ---------------------------------------------------------------------------
def generate_feedback_pipeline(
    db: Session,
    dataset_version: Optional[str] = None,
    export_dataset: bool = True,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """Inspect all stored predictions and matching operational outcomes to produce or update feedback records.

    Idempotent:
    - Does not duplicate records for the same prediction.
    - Updates existing records if outcome data changed.
    - Exports deterministic manifest and CSV snapshot when requested.
    """
    ts_now = datetime.now(timezone.utc)
    target_ds_version = dataset_version or f"FB_DS_{ts_now.strftime('%Y%m%d_%H%M%S')}"

    predictions = db.query(Prediction).all()

    processed_count = 0
    eligible_count = 0
    pending_count = 0
    excluded_count = 0
    updated_count = 0

    eligible_records_for_export: List[Dict[str, Any]] = []

    for pred in predictions:
        processed_count += 1

        # Resolve Model Version
        mv_version = None
        if pred.model_version_id:
            mv = db.query(ModelVersion).filter(ModelVersion.id == pred.model_version_id).first()
            if mv:
                mv_version = mv.version
        if not mv_version:
            mv_version = getattr(pred, "model_version_str", None) or "v1.0.0"

        # Resolve Decision & Outcome
        # 1. Try finding decision linked through recommendations
        decision = None
        rec = db.query(Recommendation).filter(Recommendation.prediction_id == pred.id).first()
        if rec:
            decision = db.query(Decision).filter(Decision.recommendation_id == rec.id).first()

        # 2. Resolve outcome linked to decision or shipment
        outcome = None
        if decision:
            outcome = db.query(Outcome).filter(Outcome.decision_id == decision.id).first()
        if not outcome and pred.shipment_id:
            outcome = db.query(Outcome).filter(Outcome.shipment_id == pred.shipment_id).first()

        # Resolve Predicted Delay
        pred_delay_dec: Optional[Decimal] = None
        if decision and decision.predicted_delay is not None:
            pred_delay_dec = round(Decimal(str(decision.predicted_delay)), 2)
        elif pred.predicted_value is not None:
            pred_delay_dec = round(Decimal(str(pred.predicted_value)), 2)
        else:
            pred_delay_dec = Decimal("0.00")

        # Validate Eligibility
        status, reason = validate_feedback_eligibility(
            prediction=pred,
            model_version=mv_version,
            outcome=outcome,
            decision=decision,
        )

        # Calculate Errors if applicable
        pred_err_dec: Optional[Decimal] = None
        abs_err_dec: Optional[Decimal] = None
        act_delay_dec: Optional[Decimal] = None
        outcome_ts: Optional[datetime] = None

        if status == "ELIGIBLE" and outcome and outcome.actual_delay is not None:
            act_delay_dec = round(Decimal(str(outcome.actual_delay)), 2)
            err_dict = calculate_prediction_error(pred_delay_dec, act_delay_dec)
            if err_dict["prediction_error"] is not None:
                pred_err_dec = Decimal(str(err_dict["prediction_error"]))
            if err_dict["absolute_error"] is not None:
                abs_err_dec = Decimal(str(err_dict["absolute_error"]))
            outcome_ts = outcome.recorded_at or outcome.updated_at
            eligible_count += 1
        elif status == "PENDING_OUTCOME":
            pending_count += 1
        else:
            excluded_count += 1

        pred_ts = pred.prediction_date or pred.created_at

        # Check existing feedback record
        existing_fb = db.query(Feedback).filter(Feedback.prediction_id == pred.prediction_id).first()

        if existing_fb:
            # Update record
            existing_fb.predicted_delay = pred_delay_dec
            existing_fb.actual_delay = act_delay_dec
            existing_fb.prediction_error = pred_err_dec
            existing_fb.absolute_error = abs_err_dec
            existing_fb.outcome_timestamp = outcome_ts
            existing_fb.model_version = mv_version
            existing_fb.feedback_status = status
            existing_fb.exclusion_reason = reason
            existing_fb.dataset_version = target_ds_version
            existing_fb.decision_id = decision.decision_id if decision else existing_fb.decision_id
            existing_fb.shipment_id = pred.shipment_id or existing_fb.shipment_id
            updated_count += 1
            fb_record = existing_fb
        else:
            fb_id = f"FB-{uuid.uuid4().hex[:8].upper()}"
            new_fb = Feedback(
                feedback_id=fb_id,
                prediction_id=pred.prediction_id,
                shipment_id=pred.shipment_id,
                decision_id=decision.decision_id if decision else None,
                predicted_delay=pred_delay_dec,
                actual_delay=act_delay_dec,
                prediction_error=pred_err_dec,
                absolute_error=abs_err_dec,
                prediction_timestamp=pred_ts,
                outcome_timestamp=outcome_ts,
                model_version=mv_version,
                feedback_status=status,
                exclusion_reason=reason,
                dataset_version=target_ds_version,
            )
            db.add(new_fb)
            fb_record = new_fb

        if status == "ELIGIBLE":
            eligible_records_for_export.append({
                "feedback_id": fb_record.feedback_id,
                "prediction_id": pred.prediction_id,
                "shipment_id": pred.shipment_id,
                "decision_id": decision.decision_id if decision else "",
                "predicted_delay": float(pred_delay_dec),
                "actual_delay": float(act_delay_dec) if act_delay_dec is not None else "",
                "prediction_error": float(pred_err_dec) if pred_err_dec is not None else "",
                "absolute_error": float(abs_err_dec) if abs_err_dec is not None else "",
                "prediction_timestamp": pred_ts.isoformat() if pred_ts else "",
                "outcome_timestamp": outcome_ts.isoformat() if outcome_ts else "",
                "model_version": mv_version,
                "feedback_status": status,
                "dataset_version": target_ds_version,
            })

    db.commit()

    manifest_path_str: Optional[str] = None
    export_path_str: Optional[str] = None

    if export_dataset:
        MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # 1. Export CSV
        csv_path = EXPORTS_DIR / f"{target_ds_version}.csv"
        headers = [
            "feedback_id", "prediction_id", "shipment_id", "decision_id",
            "predicted_delay", "actual_delay", "prediction_error", "absolute_error",
            "prediction_timestamp", "outcome_timestamp", "model_version",
            "feedback_status", "dataset_version"
        ]
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for r in eligible_records_for_export:
                writer.writerow(r)
        export_path_str = str(csv_path)

        # Compute Checksum
        hasher = hashlib.sha256()
        with open(csv_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        checksum = hasher.hexdigest()

        # Compute summary metrics for eligible slice
        summary_mae = None
        summary_rmse = None
        summary_bias = None
        if eligible_records_for_export:
            abs_errors = [r["absolute_error"] for r in eligible_records_for_export if isinstance(r["absolute_error"], (int, float))]
            signed_errors = [r["prediction_error"] for r in eligible_records_for_export if isinstance(r["prediction_error"], (int, float))]
            if abs_errors:
                summary_mae = round(sum(abs_errors) / len(abs_errors), 4)
                summary_rmse = round(math.sqrt(sum(e ** 2 for e in signed_errors) / len(signed_errors)), 4)
                summary_bias = round(sum(signed_errors) / len(signed_errors), 4)

        # 2. Export JSON Manifest
        manifest_data = {
            "dataset_version": target_ds_version,
            "created_at": ts_now.isoformat(),
            "schema_version": "1.0",
            "row_count": len(eligible_records_for_export),
            "total_processed": processed_count,
            "eligible_count": eligible_count,
            "pending_count": pending_count,
            "excluded_count": excluded_count,
            "model_versions": sorted(list({r["model_version"] for r in eligible_records_for_export})),
            "source_predictions": [r["prediction_id"] for r in eligible_records_for_export],
            "eligibility_rules": [
                "Prediction must exist and link to verified shipment",
                "Model version must be documented at prediction time",
                "Operational outcome must be DELIVERED and non-disputed",
                "Actual delay must be valid non-negative number",
                "Prediction error = actual_delay - predicted_delay"
            ],
            "metrics_summary": {
                "mae": summary_mae,
                "rmse": summary_rmse,
                "mean_signed_error": summary_bias,
            },
            "checksum": checksum,
        }
        manifest_path = MANIFESTS_DIR / f"{target_ds_version}.json"
        with open(manifest_path, mode="w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
        manifest_path_str = str(manifest_path)

    return {
        "processed_count": processed_count,
        "eligible_count": eligible_count,
        "pending_count": pending_count,
        "excluded_count": excluded_count,
        "updated_count": updated_count,
        "dataset_version": target_ds_version,
        "manifest_path": manifest_path_str,
        "export_path": export_path_str,
        "message": (
            f"Feedback generation complete: {processed_count} processed, "
            f"{eligible_count} eligible, {pending_count} pending actuals, "
            f"{excluded_count} excluded."
        ),
    }


# ---------------------------------------------------------------------------
# 4. Model Evaluation on Feedback
# ---------------------------------------------------------------------------
def evaluate_model_on_feedback(
    db: Session,
    model_version: str,
    dataset_version: Optional[str] = None,
    min_sample_threshold: int = DEFAULT_MIN_SAMPLE_THRESHOLD,
) -> Dict[str, Any]:
    """Evaluate delay prediction accuracy of a specified model version using eligible feedback records.

    Strict Guarantees:
    - Never fabricates metrics if data is insufficient.
    - Enforces sample size threshold warnings.
    - Read-only: does not retrain or promote models.
    """
    clean_version = model_version.strip()

    # Verify model version exists in model_versions or model registry
    mv_record = (
        db.query(ModelVersion)
        .filter(ModelVersion.version == clean_version)
        .first()
    )
    if not mv_record:
        # Also check without leading 'v' or with 'v'
        alt_version = clean_version[1:] if clean_version.startswith("v") else f"v{clean_version}"
        mv_record = (
            db.query(ModelVersion)
            .filter(ModelVersion.version == alt_version)
            .first()
        )

    query = (
        db.query(Feedback)
        .filter(
            func.lower(Feedback.model_version) == clean_version.lower(),
            Feedback.feedback_status == "ELIGIBLE",
            Feedback.actual_delay.isnot(None),
            Feedback.predicted_delay.isnot(None),
        )
    )

    if dataset_version:
        query = query.filter(Feedback.dataset_version == dataset_version)

    records = query.all()
    count = len(records)
    eval_ts = datetime.now(timezone.utc)

    if count == 0:
        return {
            "model_version": clean_version,
            "dataset_version": dataset_version,
            "status": "INSUFFICIENT_DATA",
            "evaluated_count": 0,
            "mae": None,
            "rmse": None,
            "mean_signed_error": None,
            "median_absolute_error": None,
            "min_error": None,
            "max_error": None,
            "is_preliminary": True,
            "warnings": [
                f"No eligible completed feedback observations found for model version '{clean_version}'."
            ],
            "interpretation": "Insufficient verified actual outcome data to compute statistical model accuracy.",
            "error_sign_convention": (
                "prediction_error = actual_delay - predicted_delay "
                "(positive = actual delay exceeded prediction / arrived later than forecast)"
            ),
            "evaluation_timestamp": eval_ts,
        }

    errors: List[float] = []
    abs_errors: List[float] = []
    sq_errors: List[float] = []

    for r in records:
        diff = float(r.prediction_error) if r.prediction_error is not None else float(r.actual_delay - r.predicted_delay)
        errors.append(diff)
        abs_errors.append(abs(diff))
        sq_errors.append(diff ** 2)

    mae = round(sum(abs_errors) / count, 4)
    rmse = round(math.sqrt(sum(sq_errors) / count), 4)
    bias = round(sum(errors) / count, 4)

    # Median absolute error
    sorted_abs = sorted(abs_errors)
    mid = count // 2
    med_ae = (
        sorted_abs[mid]
        if count % 2 != 0
        else round((sorted_abs[mid - 1] + sorted_abs[mid]) / 2.0, 4)
    )

    min_err = round(min(errors), 4)
    max_err = round(max(errors), 4)

    is_preliminary = count < min_sample_threshold
    warnings: List[str] = []
    if is_preliminary:
        warnings.append(
            f"Sample size (N={count}) is below recommended evaluation threshold (N={min_sample_threshold}). "
            "Metrics are preliminary and subject to statistical volatility."
        )

    # Directional interpretation
    if bias > 0.25:
        interp = (
            f"Model '{clean_version}' systematically underpredicts delivery delays by an average of "
            f"+{bias:.2f} days (shipments tend to arrive later than forecast)."
        )
    elif bias < -0.25:
        interp = (
            f"Model '{clean_version}' systematically overpredicts delivery delays by an average of "
            f"{bias:.2f} days (conservative forecasting; shipments arrive earlier than predicted)."
        )
    else:
        interp = (
            f"Model '{clean_version}' exhibits well-calibrated delay predictions with negligible "
            f"directional bias ({bias:+.2f} days average signed error)."
        )

    return {
        "model_version": clean_version,
        "dataset_version": dataset_version,
        "status": "EVALUATED",
        "evaluated_count": count,
        "mae": mae,
        "rmse": rmse,
        "mean_signed_error": bias,
        "median_absolute_error": med_ae,
        "min_error": min_err,
        "max_error": max_err,
        "is_preliminary": is_preliminary,
        "warnings": warnings,
        "interpretation": interp,
        "error_sign_convention": (
            "prediction_error = actual_delay - predicted_delay "
            "(positive = actual delay exceeded prediction / arrived later than forecast)"
        ),
        "evaluation_timestamp": eval_ts,
    }
