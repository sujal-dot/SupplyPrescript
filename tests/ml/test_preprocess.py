"""
Unit tests for ml/preprocess.py
===============================
Tests loading splits, feature validation, separation of X and y,
ColumnTransformer pipeline construction, and train-only fitting.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.feature_config import (
    APPROVED_FEATURES,
    CATEGORICAL_FEATURES,
    CLASSIFICATION_TARGET,
    NUMERICAL_FEATURES,
    REGRESSION_TARGET,
)
from ml.preprocess import (
    build_preprocessor,
    fit_preprocessor,
    get_target_for_task,
    get_transformed_feature_names,
    load_feature_splits,
    separate_features_and_target,
    transform_features,
    validate_feature_data,
)


@pytest.fixture
def mock_feature_df() -> pd.DataFrame:
    """Create a minimal valid feature DataFrame with target columns."""
    return pd.DataFrame({
        "supplier_reliability": [0.95, 0.88, 0.92, 0.85],
        "historical_avg_delay": [0.0, 1.2, 0.5, 2.0],
        "lead_time": [7, 5, 10, 8],
        "inventory_level": [500, 300, 700, 400],
        "demand": [450, 320, 600, 380],
        "quantity": [200, 150, 400, 250],
        "shipping_cost": [120.0, 85.5, 300.0, 175.0],
        "distance": [350.0, 850.0, 1200.0, 600.0],
        "transport_mode": ["Road", "Air", "Sea", "Rail"],
        "season": ["Winter", "Summer", "Monsoon", "Post-Monsoon"],
        "priority": ["High", "Medium", "Low", "Critical"],
        "delay_days": [0, 3, 0, 5],
        "delayed": [0, 1, 0, 1],
    })


def test_get_target_for_task():
    """Verify target resolution for tasks."""
    assert get_target_for_task("classification") == CLASSIFICATION_TARGET
    assert get_target_for_task("cls") == CLASSIFICATION_TARGET
    assert get_target_for_task("regression") == REGRESSION_TARGET
    assert get_target_for_task("reg") == REGRESSION_TARGET
    with pytest.raises(ValueError):
        get_target_for_task("unknown_task")


def test_separate_features_and_target(mock_feature_df):
    """Verify target separation and absence of target in feature matrix X."""
    X_cls, y_cls = separate_features_and_target(mock_feature_df, task="classification")
    assert CLASSIFICATION_TARGET not in X_cls.columns
    assert len(y_cls) == len(mock_feature_df)
    assert (y_cls == mock_feature_df[CLASSIFICATION_TARGET]).all()

    X_reg, y_reg = separate_features_and_target(mock_feature_df, task="regression")
    assert REGRESSION_TARGET not in X_reg.columns
    assert len(y_reg) == len(mock_feature_df)
    assert (y_reg == mock_feature_df[REGRESSION_TARGET]).all()


def test_validate_feature_data_success(mock_feature_df):
    """Clean feature DataFrame passes validation."""
    res = validate_feature_data(mock_feature_df, task="classification", raise_on_error=True)
    assert res["valid"] is True


def test_validate_feature_data_missing_column(mock_feature_df):
    """Missing required feature raises ValueError."""
    bad_df = mock_feature_df.drop(columns=["quantity"])
    with pytest.raises(ValueError, match="Missing required features"):
        validate_feature_data(bad_df, raise_on_error=True)


def test_build_and_fit_preprocessor(mock_feature_df):
    """Verify ColumnTransformer fits on training data and transforms correctly."""
    X, _ = separate_features_and_target(mock_feature_df, task="classification")
    preprocessor = build_preprocessor()
    fitted_prep = fit_preprocessor(preprocessor, X)

    X_trans = transform_features(fitted_prep, X)
    assert isinstance(X_trans, np.ndarray)
    assert X_trans.shape[0] == len(X)
    # 8 numerical + 4 transport + 4 season + 4 priority = 20 features
    assert X_trans.shape[1] == 20

    feature_names = get_transformed_feature_names(fitted_prep)
    assert len(feature_names) == 20


def test_preprocessor_handles_unseen_categories(mock_feature_df):
    """Verify preprocessor handles unseen categories at inference with handle_unknown='ignore'."""
    X_train, _ = separate_features_and_target(mock_feature_df.iloc[:2], task="classification")
    preprocessor = build_preprocessor()
    fitted_prep = fit_preprocessor(preprocessor, X_train)

    # Input with unseen transport_mode "Sea" not in the 2-row train set
    test_record = mock_feature_df.iloc[2:3].copy()
    X_test, _ = separate_features_and_target(test_record, task="classification")
    # Must not raise an exception
    X_trans = transform_features(fitted_prep, X_test)
    assert X_trans.shape[0] == 1


def test_load_feature_splits_file_not_found():
    """Verify load_feature_splits raises FileNotFoundError on invalid directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(FileNotFoundError):
            load_feature_splits("classification", custom_dir=Path(tmpdir))
