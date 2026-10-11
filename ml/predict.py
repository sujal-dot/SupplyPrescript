"""
SupplyPrescript — Inference and Prediction Engine
=================================================
High-performance, leak-free prediction service for shipment delay probability
and delay duration estimation using registered XGBoost models.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from ml.feature_config import APPROVED_FEATURES
from ml.leakage_checks import check_feature_matrix_for_leakage
from ml.model_registry import load_registered_model
from ml.preprocess import transform_features

logger = logging.getLogger("ml.predict")

# In-memory cache for loaded model artifacts to prevent repeated disk I/O
_MODEL_CACHE: Dict[str, Dict[str, Any]] = {}


def get_cached_model(task: str) -> Dict[str, Any]:
    """
    Load and cache model, preprocessor, and metadata in memory.
    """
    if task not in _MODEL_CACHE:
        model, preprocessor, metadata = load_registered_model(task)
        _MODEL_CACHE[task] = {
            "model": model,
            "preprocessor": preprocessor,
            "metadata": metadata,
        }
    return _MODEL_CACHE[task]


def clear_model_cache() -> None:
    """Clear in-memory model cache."""
    _MODEL_CACHE.clear()


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
    Predict probability of shipment delay (between 0.0 and 1.0).
    Returns 1D numpy array of probabilities.
    """
    bundle = get_cached_model("classification")
    model = bundle["model"]
    preprocessor = bundle["preprocessor"]

    X_df = prepare_input_dataframe(shipment_features)
    X_trans = transform_features(preprocessor, X_df)

    probs = model.predict_proba(X_trans)[:, 1]
    return np.clip(probs, 0.0, 1.0)


def predict_delay_days(
    shipment_features: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
) -> np.ndarray:
    """
    Predict number of delay days (non-negative float, clipped at 0).
    Returns 1D numpy array of delay day estimates.
    """
    bundle = get_cached_model("regression")
    model = bundle["model"]
    preprocessor = bundle["preprocessor"]

    X_df = prepare_input_dataframe(shipment_features)
    X_trans = transform_features(preprocessor, X_df)

    raw_preds = model.predict(X_trans)
    return np.clip(raw_preds, 0.0, None)


def predict_shipment(
    shipment_features: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
    custom_threshold: Optional[float] = None,
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Generate unified, structured prediction using both classification and regression models.
    Supports single shipment (dict) or batch shipments (list/DataFrame).
    """
    is_single_dict = isinstance(shipment_features, dict)
    X_df = prepare_input_dataframe(shipment_features)

    # Classification inference
    cls_bundle = get_cached_model("classification")
    cls_model = cls_bundle["model"]
    cls_prep = cls_bundle["preprocessor"]
    cls_meta = cls_bundle["metadata"]
    default_thresh = float(cls_meta.get("target", {}).get("classification_threshold", 0.5))
    threshold = custom_threshold if custom_threshold is not None else default_thresh

    X_cls = transform_features(cls_prep, X_df)
    probs = np.clip(cls_model.predict_proba(X_cls)[:, 1], 0.0, 1.0)
    binary_preds = (probs >= threshold).astype(bool)

    # Regression inference
    reg_bundle = get_cached_model("regression")
    reg_model = reg_bundle["model"]
    reg_prep = reg_bundle["preprocessor"]
    reg_meta = reg_bundle["metadata"]

    X_reg = transform_features(reg_prep, X_df)
    pred_days = np.clip(reg_model.predict(X_reg), 0.0, None)

    timestamp_utc = datetime.now(timezone.utc).isoformat()
    cls_version = cls_meta.get("model_version", "1.0.0")
    reg_version = reg_meta.get("model_version", "1.0.0")

    results: List[Dict[str, Any]] = []
    for is_del, prob, days in zip(binary_preds, probs, pred_days):
        prob_val = round(float(prob), 4)
        days_val = round(float(days), 2)

        # Disagreement check
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
            "model_version": f"cls:{cls_version}/reg:{reg_version}",
            "disagreement_warning": disagreement_warning,
            "prediction_timestamp": timestamp_utc,
        })

    if is_single_dict:
        return results[0]
    return results
