"""
Unit tests for ml/leakage_checks.py
===================================
Tests detection of target leakage, post-delivery leakage, identifier exclusion,
and causal independence in historical statistics.
"""

from __future__ import annotations

import pandas as pd
import pytest

from ml.feature_config import APPROVED_FEATURES
from ml.leakage_checks import (
    FeatureAvailability,
    check_feature_matrix_for_leakage,
    classify_column_availability,
    generate_leakage_report,
    verify_no_future_leakage_in_historical_stats,
)


@pytest.fixture
def clean_X_df() -> pd.DataFrame:
    """Create a clean approved feature matrix without any leakage."""
    return pd.DataFrame({col: [1.0] for col in APPROVED_FEATURES})


def test_clean_feature_matrix_passes(clean_X_df):
    """Clean feature matrix passes leakage checks."""
    res = check_feature_matrix_for_leakage(clean_X_df, raise_on_error=True)
    assert res["passed"] is True
    assert len(res["violations"]) == 0


def test_target_in_X_triggers_error(clean_X_df):
    """Presence of target column in X triggers leakage exception."""
    df_leaky = clean_X_df.copy()
    df_leaky["delay_days"] = [0]
    with pytest.raises(ValueError, match="Target column.*present in feature matrix"):
        check_feature_matrix_for_leakage(df_leaky, raise_on_error=True)

    df_leaky2 = clean_X_df.copy()
    df_leaky2["delayed"] = [1]
    with pytest.raises(ValueError, match="Target column.*present in feature matrix"):
        check_feature_matrix_for_leakage(df_leaky2, raise_on_error=True)


def test_actual_delivery_date_in_X_triggers_error(clean_X_df):
    """Presence of actual delivery date in X triggers post-delivery leakage error."""
    df_leaky = clean_X_df.copy()
    df_leaky["actual_delivery_date"] = ["2024-01-15"]
    with pytest.raises(ValueError, match="Post-delivery.*present in feature matrix"):
        check_feature_matrix_for_leakage(df_leaky, raise_on_error=True)


def test_outcome_fields_in_X_trigger_error(clean_X_df):
    """Presence of outcome fields (e.g. delivery_status, delay_reason) triggers leakage error."""
    for forbidden in ["delivery_status", "delay_reason", "lead_time_outlier"]:
        df_leaky = clean_X_df.copy()
        df_leaky[forbidden] = ["On Time"]
        with pytest.raises(ValueError, match="forbidden"):
            check_feature_matrix_for_leakage(df_leaky, raise_on_error=True)


def test_identifiers_in_X_trigger_error(clean_X_df):
    """Presence of raw IDs as numerical features triggers leakage error."""
    for id_col in ["shipment_id", "supplier_id", "product_id"]:
        df_leaky = clean_X_df.copy()
        df_leaky[id_col] = ["ID123"]
        with pytest.raises(ValueError, match="forbidden"):
            check_feature_matrix_for_leakage(df_leaky, raise_on_error=True)


def test_column_availability_classification():
    """Verify correct lifecycle availability tier classification."""
    assert classify_column_availability("supplier_reliability") == FeatureAvailability.ORDER_CREATION
    assert classify_column_availability("lead_time") == FeatureAvailability.ORDER_CREATION
    assert classify_column_availability("actual_delivery_date") == FeatureAvailability.POST_DELIVERY
    assert classify_column_availability("delay_days") == FeatureAvailability.POST_DELIVERY
    assert classify_column_availability("is_delayed") == FeatureAvailability.POST_DELIVERY
    assert classify_column_availability("unknown_foo_bar") == FeatureAvailability.UNKNOWN


def test_verify_no_future_leakage_in_historical_stats():
    """Test helper validating causal independence in historical statistics."""
    df = pd.DataFrame({
        "supplier_id": ["SUP001", "SUP001"],
        "order_date": ["2024-01-01", "2024-01-08"],
        "delay_days": [2, 5],
        "historical_avg_delay": [0.0, 2.0],
    })
    assert verify_no_future_leakage_in_historical_stats(df) is True


def test_generate_leakage_report(clean_X_df):
    """Verify generated leakage report format and PASS status."""
    report = generate_leakage_report(clean_X_df, clean_X_df, clean_X_df)
    assert report["status"] == "PASS"
    assert report["train_clean"] is True
    assert report["validation_clean"] is True
    assert report["test_clean"] is True
    assert "approved_feature_columns" in report
    assert "forbidden_leakage_columns" in report
    assert len(report["violations"]) == 0
