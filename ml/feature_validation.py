"""
SupplyPrescript — Feature Validation and Quality Reporting
==========================================================
Validates numerical and categorical distributions, checks ranges and types,
ensures target integrity, and compiles comprehensive feature quality reports.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.feature_config import (
    APPROVED_FEATURES,
    CATEGORICAL_FEATURES,
    CLASSIFICATION_TARGET,
    NUMERICAL_FEATURES,
    REGRESSION_TARGET,
    VALID_PRIORITIES,
    VALID_SEASONS,
    VALID_TRANSPORT_MODES,
)

logger = logging.getLogger("ml.feature_validation")


class FeatureValidationError(ValueError):
    """Raised when critical feature validation assertions fail."""
    pass


def validate_numerical_features(
    df: pd.DataFrame,
    features: Optional[List[str]] = None,
    raise_on_error: bool = True,
) -> Dict[str, Any]:
    """
    Validate numerical feature constraints:
    - No NaN/nulls
    - No infinite values
    - Valid value bounds per domain business rules
    """
    if features is None:
        features = NUMERICAL_FEATURES

    errors: List[str] = []
    warnings: List[str] = []

    for feat in features:
        if feat not in df.columns:
            errors.append(f"Missing required numerical feature column: '{feat}'")
            continue

        series = df[feat]

        # 1. Null check
        n_null = int(series.isna().sum())
        if n_null > 0:
            errors.append(f"Feature '{feat}' contains {n_null} null/NaN values.")

        # 2. Infinite check
        if pd.api.types.is_numeric_dtype(series):
            n_inf = int(np.isinf(series).sum())
            if n_inf > 0:
                errors.append(f"Feature '{feat}' contains {n_inf} infinite values.")
        else:
            errors.append(f"Feature '{feat}' is not numeric dtype (got {series.dtype}).")
            continue

        # 3. Domain business range checks
        if feat == "supplier_reliability":
            if (series < 0.0).any() or (series > 1.0).any():
                errors.append(f"'{feat}' values outside [0.0, 1.0]. Min: {series.min()}, Max: {series.max()}")

        elif feat == "historical_avg_delay":
            if (series < 0.0).any():
                errors.append(f"'{feat}' contains negative delay values. Min: {series.min()}")

        elif feat == "lead_time":
            if (series <= 0).any():
                errors.append(f"'{feat}' (planned lead time) contains non-positive values. Min: {series.min()}")

        elif feat == "quantity":
            if (series <= 0).any():
                errors.append(f"'{feat}' contains non-positive values. Min: {series.min()}")

        elif feat == "shipping_cost":
            if (series < 0.0).any():
                errors.append(f"'{feat}' contains negative costs. Min: {series.min()}")

        elif feat == "inventory_level":
            if (series < 0).any():
                errors.append(f"'{feat}' contains negative inventory. Min: {series.min()}")

        elif feat == "demand":
            if (series < 0).any():
                errors.append(f"'{feat}' contains negative demand. Min: {series.min()}")

        elif feat == "distance":
            if (series <= 0).any():
                errors.append(f"'{feat}' contains non-positive distance. Min: {series.min()}")

    is_valid = len(errors) == 0
    if not is_valid:
        logger.error("Numerical validation failed with %d error(s): %s", len(errors), errors)
        if raise_on_error:
            raise FeatureValidationError(f"Numerical validation failed: {errors}")
    else:
        logger.info("Numerical validation passed for all %d features.", len(features))

    return {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "validated_features": features,
    }


def validate_categorical_features(
    df: pd.DataFrame,
    features: Optional[List[str]] = None,
    raise_on_error: bool = True,
) -> Dict[str, Any]:
    """
    Validate categorical feature constraints:
    - No empty/whitespace strings
    - Categorical members belong to canonical category sets
    """
    if features is None:
        features = CATEGORICAL_FEATURES

    errors: List[str] = []
    allowed_maps = {
        "transport_mode": VALID_TRANSPORT_MODES,
        "season": VALID_SEASONS,
        "priority": VALID_PRIORITIES,
    }

    for feat in features:
        if feat not in df.columns:
            errors.append(f"Missing required categorical feature column: '{feat}'")
            continue

        series = df[feat].astype(str)

        # Check for empty or whitespace
        empty_count = int(series.str.strip().eq("").sum())
        if empty_count > 0:
            errors.append(f"Categorical feature '{feat}' has {empty_count} empty strings.")

        # Check membership
        if feat in allowed_maps:
            valid_set = allowed_maps[feat]
            invalid_vals = set(series.unique()) - valid_set
            if invalid_vals:
                errors.append(f"Feature '{feat}' has unrecognized categories: {invalid_vals}. Allowed: {valid_set}")

    is_valid = len(errors) == 0
    if not is_valid:
        logger.error("Categorical validation failed: %s", errors)
        if raise_on_error:
            raise FeatureValidationError(f"Categorical validation failed: {errors}")
    else:
        logger.info("Categorical validation passed for all %d features.", len(features))

    return {
        "valid": is_valid,
        "errors": errors,
        "validated_features": features,
    }


def validate_targets(
    df: pd.DataFrame,
    regression_target: str = REGRESSION_TARGET,
    classification_target: str = CLASSIFICATION_TARGET,
    raise_on_error: bool = True,
) -> Dict[str, Any]:
    """
    Validate target variable properties:
    - delay_days >= 0, integer
    - delayed in {0, 1}, integer
    - delayed == (delay_days > 0).astype(int)
    """
    errors: List[str] = []

    # Regression target
    if regression_target in df.columns:
        reg_s = df[regression_target]
        if reg_s.isna().any():
            errors.append(f"Regression target '{regression_target}' contains null values.")
        if (reg_s < 0).any():
            errors.append(f"Regression target '{regression_target}' contains negative values.")
    else:
        errors.append(f"Regression target '{regression_target}' not found.")

    # Classification target
    if classification_target in df.columns:
        cls_s = df[classification_target]
        if cls_s.isna().any():
            errors.append(f"Classification target '{classification_target}' contains null values.")
        unique_vals = set(cls_s.unique())
        if not unique_vals.issubset({0, 1}):
            errors.append(f"Classification target '{classification_target}' values must be in {{0, 1}}, got: {unique_vals}")
    else:
        errors.append(f"Classification target '{classification_target}' not found.")

    # Consistency between regression and classification targets
    if regression_target in df.columns and classification_target in df.columns:
        expected_classification = (df[regression_target] > 0).astype(int)
        mismatches = int((df[classification_target] != expected_classification).sum())
        if mismatches > 0:
            errors.append(
                f"Target inconsistency: {mismatches} rows differ between '{classification_target}' and ('{regression_target}' > 0)."
            )

    is_valid = len(errors) == 0
    if not is_valid:
        logger.error("Target validation failed: %s", errors)
        if raise_on_error:
            raise FeatureValidationError(f"Target validation failed: {errors}")
    else:
        logger.info("Target validation passed successfully.")

    return {
        "valid": is_valid,
        "errors": errors,
    }


def compile_feature_report(
    df_raw: pd.DataFrame,
    df_features: pd.DataFrame,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    rejected_rows_count: int,
    date_min: str,
    date_max: str,
    warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compile a complete, publication-grade feature quality report.
    """
    if warnings is None:
        warnings = []

    # Numerical summaries
    num_summary: Dict[str, Dict[str, float]] = {}
    for col in NUMERICAL_FEATURES:
        if col in df_features.columns:
            s = df_features[col]
            num_summary[col] = {
                "count": float(len(s)),
                "min": round(float(s.min()), 4),
                "max": round(float(s.max()), 4),
                "mean": round(float(s.mean()), 4),
                "std": round(float(s.std()), 4),
                "median": round(float(s.median()), 4),
                "q25": round(float(s.quantile(0.25)), 4),
                "q75": round(float(s.quantile(0.75)), 4),
            }

    # Categorical distributions
    cat_summary: Dict[str, Dict[str, int]] = {}
    for col in CATEGORICAL_FEATURES:
        if col in df_features.columns:
            cat_summary[col] = {str(k): int(v) for k, v in df_features[col].value_counts().items()}

    # Target distributions
    reg_summary: Dict[str, Any] = {}
    if REGRESSION_TARGET in df_features.columns:
        s = df_features[REGRESSION_TARGET]
        reg_summary = {
            "min": int(s.min()),
            "max": int(s.max()),
            "mean": round(float(s.mean()), 4),
            "median": int(s.median()),
            "zero_delay_count (on_time)": int((s == 0).sum()),
            "positive_delay_count (delayed)": int((s > 0).sum()),
        }

    cls_summary: Dict[str, Any] = {}
    if CLASSIFICATION_TARGET in df_features.columns:
        s = df_features[CLASSIFICATION_TARGET]
        delayed_count = int((s == 1).sum())
        on_time_count = int((s == 0).sum())
        total_count = len(s)
        delayed_pct = round(float(delayed_count / total_count * 100), 2) if total_count > 0 else 0.0
        cls_summary = {
            "on_time_count (0)": on_time_count,
            "delayed_count (1)": delayed_count,
            "delayed_percentage": delayed_pct,
            "class_imbalance_ratio (0:1)": f"{round(on_time_count / max(1, delayed_count), 2)} : 1",
            "imbalance_severity": "Moderate (suitable for AUC-ROC / PR-AUC and class-weighted training)" if 10 <= delayed_pct <= 40 else "Severe",
        }

    # Missing values per feature
    missing_per_feat = {
        col: int(df_features[col].isna().sum())
        for col in APPROVED_FEATURES
        if col in df_features.columns
    }

    total_rows = len(df_features)
    duplicates = int(df_features[APPROVED_FEATURES].duplicated().sum())

    report = {
        "dataset_metrics": {
            "input_row_count": len(df_raw),
            "output_row_count": total_rows,
            "rejected_row_count": rejected_rows_count,
            "retention_rate_pct": round(total_rows / len(df_raw) * 100, 2) if len(df_raw) > 0 else 0.0,
            "feature_column_count": len(APPROVED_FEATURES),
            "duplicate_records_in_features": duplicates,
            "date_range": {
                "start_order_date": str(date_min),
                "end_order_date": str(date_max),
            },
        },
        "split_sizes": {
            "train": {
                "row_count": len(train_df),
                "percentage": round(len(train_df) / total_rows * 100, 2) if total_rows > 0 else 0.0,
            },
            "validation": {
                "row_count": len(val_df),
                "percentage": round(len(val_df) / total_rows * 100, 2) if total_rows > 0 else 0.0,
            },
            "test": {
                "row_count": len(test_df),
                "percentage": round(len(test_df) / total_rows * 100, 2) if total_rows > 0 else 0.0,
            },
        },
        "missing_values_per_feature": missing_per_feat,
        "numerical_features_summary": num_summary,
        "categorical_features_summary": cat_summary,
        "regression_target_summary": reg_summary,
        "classification_target_summary": cls_summary,
        "validation_warnings": warnings,
        "validation_status": "PASS" if not warnings else "PASS_WITH_WARNINGS",
    }

    return report
