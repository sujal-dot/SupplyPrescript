"""SupplyPrescript — XGBoost Model Retraining Engine (Day 23)
===========================================================
Executes isolated candidate retraining combining historical validated data and verified
feedback actuals. Reuses Day 6 feature pipeline, Day 7 training procedures, and Day 8 registry
specifications without overwriting active production artifacts.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier, XGBRegressor

from ml.evaluate import (
    evaluate_classification,
    evaluate_regression,
    find_optimal_threshold,
)
from ml.feature_config import (
    APPROVED_FEATURES,
    CLASSIFICATION_TARGET,
    DEFAULT_INPUT_PATH,
    PROJECT_ROOT,
    RANDOM_SEED,
    REGRESSION_TARGET,
)
from ml.leakage_checks import check_feature_matrix_for_leakage
from ml.model_registry import (
    compute_file_checksum,
    get_active_model_version,
)
from ml.preprocess import (
    build_preprocessor,
    fit_preprocessor,
    load_feature_splits,
    separate_features_and_target,
    transform_features,
)

logger = logging.getLogger("ml.retrain")

CANDIDATES_ROOT_DIR = PROJECT_ROOT / "ml" / "artifacts" / "candidates"


def get_next_candidate_version(current_version: Optional[str] = None) -> str:
    """Safely allocate the next candidate version string (e.g. 'v1.0' -> 'v1.1' or 'v1.0.0' -> 'v1.1.0')."""
    base = current_version or get_active_model_version()
    clean = base.strip().lstrip("vV")
    parts = clean.split(".")

    try:
        if len(parts) >= 2:
            major = int(parts[0])
            minor = int(parts[1]) + 1
            if len(parts) == 3:
                patch = parts[2]
                return f"v{major}.{minor}.{patch}"
            return f"v{major}.{minor}"
        elif len(parts) == 1:
            major = int(parts[0])
            return f"v{major}.1"
    except Exception:
        pass
    return f"v{clean}-candidate"


def compute_dataframe_fingerprint(df: pd.DataFrame) -> str:
    """Compute deterministic SHA-256 fingerprint for a pandas DataFrame."""
    buf = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(buf).hexdigest()


def prepare_retraining_dataset(
    feedback_df: Optional[pd.DataFrame] = None,
    base_splits_dir: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    """Prepare candidate training dataset combining historical splits with verified feedback actuals.

    Rules:
    - Target for regression: delay_days (actual observed delay).
    - Target for classification: delayed (1 if actual_delay > 0.0 else 0).
    - Features: strictly the 11 approved features.
    - Leakage checks: verifies no post-order outcome columns exist in X.
    - Preserves chronological holdout for unbiased validation.

    Returns:
        (train_df, val_df, test_df, dataset_fingerprint)
    """
    # Load historical Day 6 regression splits
    base_train, base_val, base_test = load_feature_splits(task="regression", custom_dir=base_splits_dir)

    # Ensure required target and features exist
    combined_train = base_train.copy()
    combined_val = base_val.copy()
    combined_test = base_test.copy()

    if feedback_df is not None and not feedback_df.empty:
        logger.info("Integrating %d verified feedback records into training set", len(feedback_df))

        # Check required columns in feedback_df
        required_cols = list(APPROVED_FEATURES)
        for col in required_cols:
            if col not in feedback_df.columns:
                raise ValueError(f"Feedback dataset is missing required feature '{col}'")

        # Set target columns
        fb_clean = feedback_df.copy()
        if "delay_days" not in fb_clean.columns:
            if "actual_delay" in fb_clean.columns:
                fb_clean["delay_days"] = fb_clean["actual_delay"].astype(float)
            else:
                raise ValueError("Feedback dataset missing 'delay_days' or 'actual_delay' target column.")

        if "delayed" not in fb_clean.columns:
            fb_clean["delayed"] = (fb_clean["delay_days"] > 0.0).astype(int)

        # Leakage check on feedback features
        check_feature_matrix_for_leakage(fb_clean[APPROVED_FEATURES])

        # Chronological allocation: 70% of new feedback to train, 15% to val, 15% to test
        n_fb = len(fb_clean)
        n_train = int(n_fb * 0.70)
        n_val = int(n_fb * 0.15)

        fb_train = fb_clean.iloc[:n_train]
        fb_val = fb_clean.iloc[n_train : n_train + n_val]
        fb_test = fb_clean.iloc[n_train + n_val :]

        combined_train = pd.concat([combined_train, fb_train], ignore_index=True)
        if not fb_val.empty:
            combined_val = pd.concat([combined_val, fb_val], ignore_index=True)
        if not fb_test.empty:
            combined_test = pd.concat([combined_test, fb_test], ignore_index=True)

    fingerprint = compute_dataframe_fingerprint(combined_train)
    return combined_train, combined_val, combined_test, fingerprint


def train_candidate_models(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    candidate_version: str,
    output_dir: Optional[Path] = None,
    random_seed: int = RANDOM_SEED,
) -> Dict[str, Any]:
    """Train XGBoost candidate models (regression & classification) and save in candidate-specific directory.

    Guarantees:
    - Candidate artifacts are isolated in ml/artifacts/candidates/{candidate_version}/.
    - Never overwrites active production artifacts.
    - Generates training manifest, checksums, and evaluation reports.

    Returns:
        Structured training job result dictionary.
    """
    logger.info("=" * 60)
    logger.info("Starting XGBoost Candidate Training for Version '%s'", candidate_version)
    logger.info("=" * 60)

    target_dir = output_dir or (CANDIDATES_ROOT_DIR / candidate_version)
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Feature separation
    X_train_df, y_train_reg = separate_features_and_target(train_df, task="regression")
    X_val_df, y_val_reg = separate_features_and_target(val_df, task="regression")
    X_test_df, y_test_reg = separate_features_and_target(test_df, task="regression")

    # Target for classification (robust to missing/NaN values)
    if "delayed" in train_df.columns:
        y_train_cls = train_df["delayed"].fillna(y_train_reg > 0.0).astype(bool).astype(int)
    else:
        y_train_cls = (y_train_reg > 0.0).astype(int)

    if "delayed" in val_df.columns:
        y_val_cls = val_df["delayed"].fillna(y_val_reg > 0.0).astype(bool).astype(int)
    else:
        y_val_cls = (y_val_reg > 0.0).astype(int)

    if "delayed" in test_df.columns:
        y_test_cls = test_df["delayed"].fillna(y_test_reg > 0.0).astype(bool).astype(int)
    else:
        y_test_cls = (y_test_reg > 0.0).astype(int)

    # 2. Leakage checks
    check_feature_matrix_for_leakage(X_train_df)
    check_feature_matrix_for_leakage(X_val_df)
    check_feature_matrix_for_leakage(X_test_df)

    # 3. Fit preprocessor on training data only
    preprocessor = build_preprocessor()
    fit_preprocessor(preprocessor, X_train_df)

    X_train = transform_features(preprocessor, X_train_df)
    X_val = transform_features(preprocessor, X_val_df)
    X_test = transform_features(preprocessor, X_test_df)

    # 4. Train XGBRegressor
    reg_params = {
        "n_estimators": 400,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "objective": "reg:squarederror",
        "random_state": random_seed,
        "n_jobs": -1,
    }
    regressor = XGBRegressor(**reg_params)
    logger.info("Fitting candidate XGBRegressor...")
    regressor.fit(X_train, y_train_reg, eval_set=[(X_val, y_val_reg)], verbose=False)

    val_reg_preds = np.clip(regressor.predict(X_val), 0.0, None)
    test_reg_preds = np.clip(regressor.predict(X_test), 0.0, None)

    val_reg_metrics = evaluate_regression(y_true=y_val_reg.to_numpy(), y_pred=val_reg_preds)
    test_reg_metrics = evaluate_regression(y_true=y_test_reg.to_numpy(), y_pred=test_reg_preds)

    # 5. Train XGBClassifier
    n_neg = int((y_train_cls == 0).sum())
    n_pos = int((y_train_cls == 1).sum())
    scale_pos = (n_neg / max(1, n_pos))

    cls_params = {
        "n_estimators": 350,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "scale_pos_weight": scale_pos,
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "random_state": random_seed,
        "n_jobs": -1,
    }
    classifier = XGBClassifier(**cls_params)
    logger.info("Fitting candidate XGBClassifier...")

    val_cls_eval_set = [(X_val, y_val_cls)] if len(np.unique(y_val_cls)) >= 2 else None
    classifier.fit(X_train, y_train_cls, eval_set=val_cls_eval_set, verbose=False)

    val_cls_probs = classifier.predict_proba(X_val)[:, 1]
    best_thresh, _ = find_optimal_threshold(y_true=y_val_cls.to_numpy(), y_prob=val_cls_probs, metric="f1")

    val_cls_metrics = evaluate_classification(
        y_true=y_val_cls.to_numpy(),
        y_prob=val_cls_probs,
        threshold=best_thresh,
    )

    test_cls_probs = classifier.predict_proba(X_test)[:, 1]
    test_cls_metrics = evaluate_classification(
        y_true=y_test_cls.to_numpy(),
        y_prob=test_cls_probs,
        threshold=best_thresh,
    )

    # 6. Save candidate artifacts into isolated directory
    clf_path = target_dir / "classifier.pkl"
    reg_path = target_dir / "regressor.pkl"
    prep_path = target_dir / "preprocessor.pkl"
    meta_path = target_dir / "metadata.json"
    metrics_path = target_dir / "metrics.json"

    joblib.dump(classifier, clf_path)
    joblib.dump(regressor, reg_path)
    joblib.dump(preprocessor, prep_path)

    checksums = {
        "classifier.pkl": compute_file_checksum(clf_path),
        "regressor.pkl": compute_file_checksum(reg_path),
        "preprocessor.pkl": compute_file_checksum(prep_path),
    }

    now_utc = datetime.now(timezone.utc).isoformat()
    meta_data = {
        "version": candidate_version,
        "model_name": "supplyprescript_delay_engine",
        "trained_at_utc": now_utc,
        "random_seed": random_seed,
        "framework_versions": {
            "python": sys.version.split()[0],
            "joblib": joblib.__version__,
        },
        "features": {
            "feature_names": APPROVED_FEATURES,
            "feature_count": len(APPROVED_FEATURES),
        },
        "targets": {
            "classification": CLASSIFICATION_TARGET,
            "regression": REGRESSION_TARGET,
        },
        "classification_threshold": best_thresh,
        "row_counts": {
            "train": len(train_df),
            "val": len(val_df),
            "test": len(test_df),
            "total": len(train_df) + len(val_df) + len(test_df),
        },
        "checksums": checksums,
        "candidate_status": "TRAINED",
    }

    metrics_data = {
        "regression": test_reg_metrics,
        "classification": test_cls_metrics,
        "validation_regression": val_reg_metrics,
        "validation_classification": val_cls_metrics,
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_data, f, indent=2)

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)

    logger.info("Candidate artifacts saved successfully in: %s", target_dir)

    return {
        "status": "SUCCESS",
        "candidate_version": candidate_version,
        "candidate_dir": str(target_dir),
        "test_regression_metrics": test_reg_metrics,
        "test_classification_metrics": test_cls_metrics,
        "checksums": checksums,
        "training_timestamp": now_utc,
    }
