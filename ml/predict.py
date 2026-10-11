"""
SupplyPrescript — Inference and Prediction Engine
=================================================
Production prediction service for shipment delay probability and duration estimation.
Loads and caches the active registered model version (e.g. 'v1.0') from models/versions/.
Provides single, batch, and API-ready inference with input validation and non-negative clipping.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from ml.feature_config import APPROVED_FEATURES
from ml.leakage_checks import check_feature_matrix_for_leakage
from ml.model_registry import (
    get_active_model_version,
    load_model_version,
    load_registered_model,
)
from ml.preprocess import transform_features

logger = logging.getLogger("ml.predict")

# In-memory bundle cache for active registered model artifacts
_ACTIVE_BUNDLE: Optional[Dict[str, Any]] = None
_LEGACY_CACHE: Dict[str, Dict[str, Any]] = {}


def get_active_bundle() -> Dict[str, Any]:
    """
    Retrieve and cache the active registered model version bundle in memory.
    Reloads if the active version pointer has changed.
    """
    global _ACTIVE_BUNDLE
    active_version = get_active_model_version()

    if _ACTIVE_BUNDLE is None or _ACTIVE_BUNDLE.get("version") != active_version:
        try:
            _ACTIVE_BUNDLE = load_model_version(active_version)
            logger.info("Loaded active model version '%s' into inference memory.", active_version)
        except Exception as e:
            logger.warning(
                "Could not load active model version '%s' from models/versions/ (%s). "
                "Attempting fallback to legacy artifact storage.",
                active_version, e,
            )
            cls_model, cls_prep, cls_meta = load_registered_model("classification")
            reg_model, reg_prep, reg_meta = load_registered_model("regression")
            _ACTIVE_BUNDLE = {
                "classifier": cls_model,
                "regressor": reg_model,
                "preprocessor": cls_prep,
                "metadata": cls_meta,
                "metrics": {},
                "version": active_version,
            }

    return _ACTIVE_BUNDLE


def reload_active_model() -> str:
    """
    Force reload the active model bundle into memory, clearing any cached artifacts.
    Returns the newly active version string.
    """
    global _ACTIVE_BUNDLE
    _ACTIVE_BUNDLE = None
    _LEGACY_CACHE.clear()
    bundle = get_active_bundle()
    return str(bundle["version"])


def clear_model_cache() -> None:
    """Clear in-memory model caches."""
    global _ACTIVE_BUNDLE
    _ACTIVE_BUNDLE = None
    _LEGACY_CACHE.clear()


def get_cached_model(task: str) -> Dict[str, Any]:
    """
    Backward-compatible task-specific bundle getter.
    """
    bundle = get_active_bundle()
    if task.lower() in ("classification", "cls"):
        return {
            "model": bundle["classifier"],
            "preprocessor": bundle["preprocessor"],
            "metadata": bundle["metadata"],
            "version": bundle["version"],
        }
    elif task.lower() in ("regression", "reg"):
        return {
            "model": bundle["regressor"],
            "preprocessor": bundle["preprocessor"],
            "metadata": bundle["metadata"],
            "version": bundle["version"],
        }
    else:
        raise ValueError(f"Unknown task '{task}'. Expected 'classification' or 'regression'.")


def prepare_input_dataframe(
    shipment_features: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
) -> pd.DataFrame:
    """
    Convert dictionary, list of dictionaries, or DataFrame into a validated DataFrame
    containing exactly the approved features.
    """
    if isinstance(shipment_features, pd.DataFrame):
        df = shipment_features.copy()
    elif isinstance(shipment_features, dict):
        df = pd.DataFrame([shipment_features])
    elif isinstance(shipment_features, list):
        if not shipment_features:
            raise ValueError("Input shipment_features list is empty.")
        df = pd.DataFrame(shipment_features)
    else:
        raise TypeError(f"Unsupported shipment_features type: {type(shipment_features)}")

    # Check for missing required features
    missing_cols = [col for col in APPROVED_FEATURES if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required shipment feature(s): {missing_cols}")

    # Subset and order by approved features
    df_clean = df[APPROVED_FEATURES].copy()

    # Leakage check: ensure no forbidden target or post-delivery columns exist
    check_feature_matrix_for_leakage(df_clean)

    return df_clean


def predict_delay_probability(
    shipment_features: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
) -> np.ndarray:
    """
    Predict probability of shipment delay (between 0.0 and 1.0) using the active model.
    Returns 1D numpy array of probabilities.
    """
    bundle = get_active_bundle()
    clf = bundle["classifier"]
    preprocessor = bundle["preprocessor"]

    X_df = prepare_input_dataframe(shipment_features)
    X_trans = transform_features(preprocessor, X_df)

    probs = clf.predict_proba(X_trans)[:, 1]
    return np.clip(probs, 0.0, 1.0)


def predict_delay_days(
    shipment_features: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
) -> np.ndarray:
    """
    Predict number of delay days (non-negative float, clipped at 0) using the active model.
    Returns 1D numpy array of delay day estimates.
    """
    bundle = get_active_bundle()
    reg = bundle["regressor"]
    preprocessor = bundle["preprocessor"]

    X_df = prepare_input_dataframe(shipment_features)
    X_trans = transform_features(preprocessor, X_df)

    raw_preds = reg.predict(X_trans)
    return np.clip(raw_preds, 0.0, None)


def predict_shipment(
    shipment_features: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
    custom_threshold: Optional[float] = None,
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Generate unified prediction using both classification and regression models
    from the active registered model version (e.g. 'v1.0').
    Supports single shipment (dict) or batch shipments (list/DataFrame).
    """
    is_single_dict = isinstance(shipment_features, dict)
    X_df = prepare_input_dataframe(shipment_features)

    bundle = get_active_bundle()
    cls_model = bundle["classifier"]
    reg_model = bundle["regressor"]
    prep = bundle["preprocessor"]
    meta = bundle.get("metadata", {})
    active_version = bundle.get("version", "v1.0")

    # Threshold: custom override > metadata threshold > fallback 0.150
    default_thresh = float(
        meta.get("classification_threshold")
        or meta.get("target", {}).get("classification_threshold")
        or 0.150
    )
    threshold = custom_threshold if custom_threshold is not None else default_thresh

    # Preprocessing
    X_trans = transform_features(prep, X_df)

    # Classification
    probs = np.clip(cls_model.predict_proba(X_trans)[:, 1], 0.0, 1.0)
    binary_preds = (probs >= threshold).astype(bool)

    # Regression with non-negative guarantee
    raw_days = reg_model.predict(X_trans)
    pred_days = np.clip(raw_days, 0.0, None)

    timestamp_utc = datetime.now(timezone.utc).isoformat()

    results: List[Dict[str, Any]] = []
    for is_del, prob, days in zip(binary_preds, probs, pred_days):
        prob_val = round(float(prob), 4)
        days_val = round(float(days), 2)

        # Disagreement check between classification and regression
        disagreement_warning: Optional[str] = None
        if not is_del and days_val > 0.5:
            disagreement_warning = (
                f"Model disagreement: Classifier predicts On-Time (P={prob_val:.2f} < {threshold:.2f}) "
                f"while Regressor predicts {days_val:.1f} days delay."
            )
        elif is_del and days_val < 0.2:
            disagreement_warning = (
                f"Model disagreement: Classifier predicts Delay (P={prob_val:.2f} >= {threshold:.2f}) "
                f"while Regressor predicts negligible delay ({days_val:.1f} days)."
            )

        results.append({
            "delayed": bool(is_del),
            "delay_probability": prob_val,
            "predicted_delay_days": days_val,
            "classification_threshold": threshold,
            "model_version": active_version,
            "disagreement_warning": disagreement_warning,
            "prediction_timestamp": timestamp_utc,
        })

    if is_single_dict:
        return results[0]
    return results
