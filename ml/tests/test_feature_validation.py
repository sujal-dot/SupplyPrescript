"""
Unit tests for ml/feature_validation.py
======================================
Tests numerical range checks, categorical validation, target consistency,
and feature reporting functionality.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.feature_config import (
    APPROVED_FEATURES,
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
)
from ml.feature_validation import (
    FeatureValidationError,
    compile_feature_report,
    validate_categorical_features,
    validate_numerical_features,
    validate_targets,
)


@pytest.fixture
def valid_features_df() -> pd.DataFrame:
    """Create a minimal valid feature matrix DataFrame."""
    return pd.DataFrame({
        "supplier_reliability": [0.95, 0.88, 0.99],
        "historical_avg_delay": [0.0, 1.5, 2.2],
        "lead_time": [7, 5, 12],
        "inventory_level": [1000, 500, 250],
        "demand": [800, 600, 200],
        "quantity": [500, 400, 150],
        "shipping_cost": [250.0, 180.5, 95.0],
        "distance": [350.0, 1100.0, 850.0],
        "transport_mode": ["Road", "Air", "Sea"],
        "season": ["Winter", "Monsoon", "Summer"],
        "priority": ["High", "Medium", "Critical"],
    })


def test_validate_numerical_features_success(valid_features_df):
    """Clean numerical features pass without error."""
    res = validate_numerical_features(valid_features_df, raise_on_error=True)
    assert res["valid"] is True
    assert len(res["errors"]) == 0


def test_validate_numerical_features_nan_fails(valid_features_df):
    """NaN in numerical column triggers validation failure."""
    df_invalid = valid_features_df.copy()
    df_invalid.loc[0, "supplier_reliability"] = np.nan
    with pytest.raises(FeatureValidationError):
        validate_numerical_features(df_invalid, raise_on_error=True)


def test_validate_numerical_features_infinite_fails(valid_features_df):
    """Infinite value triggers validation failure."""
    df_invalid = valid_features_df.copy()
    df_invalid.loc[1, "distance"] = np.inf
    with pytest.raises(FeatureValidationError):
        validate_numerical_features(df_invalid, raise_on_error=True)


def test_validate_numerical_features_negative_quantity_fails(valid_features_df):
    """Negative quantity triggers validation failure."""
    df_invalid = valid_features_df.copy()
    df_invalid.loc[0, "quantity"] = -10
    with pytest.raises(FeatureValidationError):
        validate_numerical_features(df_invalid, raise_on_error=True)


def test_validate_numerical_features_invalid_reliability_fails(valid_features_df):
    """Supplier reliability > 1.0 triggers failure."""
    df_invalid = valid_features_df.copy()
    df_invalid.loc[0, "supplier_reliability"] = 1.25
    with pytest.raises(FeatureValidationError):
        validate_numerical_features(df_invalid, raise_on_error=True)


def test_validate_categorical_features_success(valid_features_df):
    """Canonical categories pass validation."""
    res = validate_categorical_features(valid_features_df, raise_on_error=True)
    assert res["valid"] is True
    assert len(res["errors"]) == 0


def test_validate_categorical_features_invalid_category_fails(valid_features_df):
    """Unrecognized category triggers validation error."""
    df_invalid = valid_features_df.copy()
    df_invalid.loc[0, "transport_mode"] = "Hyperloop"
    with pytest.raises(FeatureValidationError):
        validate_categorical_features(df_invalid, raise_on_error=True)


def test_validate_categorical_features_empty_string_fails(valid_features_df):
    """Empty string triggers validation error."""
    df_invalid = valid_features_df.copy()
    df_invalid.loc[0, "priority"] = "   "
    with pytest.raises(FeatureValidationError):
        validate_categorical_features(df_invalid, raise_on_error=True)


def test_validate_targets_success():
    """Consistent non-negative targets pass."""
    df = pd.DataFrame({
        "delay_days": [0, 4, 0, 7],
        "delayed": [0, 1, 0, 1],
    })
    res = validate_targets(df, raise_on_error=True)
    assert res["valid"] is True


def test_validate_targets_inconsistency_fails():
    """Inconsistency between delayed flag and delay_days triggers error."""
    df = pd.DataFrame({
        "delay_days": [0, 4],
        "delayed": [1, 0],  # Inconsistent: 0 delay marked as delayed, 4 delay marked as on-time
    })
    with pytest.raises(FeatureValidationError):
        validate_targets(df, raise_on_error=True)


def test_compile_feature_report_structure(valid_features_df):
    """Verify feature report JSON contains all expected top-level sections."""
    df = valid_features_df.copy()
    df["delay_days"] = [0, 2, 0]
    df["delayed"] = [0, 1, 0]

    report = compile_feature_report(
        df_raw=df,
        df_features=df,
        train_df=df.iloc[:2],
        val_df=df.iloc[2:],
        test_df=df.iloc[2:],
        rejected_rows_count=0,
        date_min="2024-01-01",
        date_max="2024-01-15",
    )
    assert "dataset_metrics" in report
    assert "split_sizes" in report
    assert "missing_values_per_feature" in report
    assert "numerical_features_summary" in report
    assert "categorical_features_summary" in report
    assert "regression_target_summary" in report
    assert "classification_target_summary" in report
    assert report["dataset_metrics"]["feature_column_count"] == len(APPROVED_FEATURES)
