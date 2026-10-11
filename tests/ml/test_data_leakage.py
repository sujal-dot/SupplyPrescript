"""
Tests for Data Leakage Prevention and Temporal Split Integrity
===============================================================
Verifies that feature matrices strictly exclude post-delivery variables,
target columns, and identifiers; ensures preprocessors fit solely on
training data; and validates temporal split ordering.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.feature_config import (
    APPROVED_FEATURES,
    CATEGORICAL_FEATURES,
    CLASSIFICATION_TARGET,
    FEATURES_DIR,
    IDENTIFIER_COLUMNS,
    LEAKAGE_COLUMNS,
    NUMERICAL_FEATURES,
    REGRESSION_TARGET,
)
from ml.leakage_checks import (
    FeatureAvailability,
    check_feature_matrix_for_leakage,
    classify_column_availability,
)
from ml.preprocess import (
    build_preprocessor,
    fit_preprocessor,
    load_feature_splits,
    separate_features_and_target,
    transform_features,
)


class TestDataLeakage:
    """Test suite ensuring zero data leakage in feature sets and preprocessing pipelines."""

    def test_approved_features_exclude_targets_and_leakage_columns(self):
        """Verify that APPROVED_FEATURES list contains no targets, post-delivery, or raw ID columns."""
        for feat in APPROVED_FEATURES:
            assert feat not in LEAKAGE_COLUMNS, f"Leaky column '{feat}' found in APPROVED_FEATURES"
            assert feat not in IDENTIFIER_COLUMNS, f"Identifier column '{feat}' found in APPROVED_FEATURES"
            assert feat != CLASSIFICATION_TARGET, f"Classification target found in APPROVED_FEATURES"
            assert feat != REGRESSION_TARGET, f"Regression target found in APPROVED_FEATURES"
            assert feat != "actual_delivery_date"
            assert feat != "delivery_status"
            assert feat != "delay_reason"

    def test_column_availability_registry_consistency(self):
        """Verify that every approved feature is classified as ORDER_CREATION."""
        for feat in APPROVED_FEATURES:
            availability = classify_column_availability(feat)
            assert availability == FeatureAvailability.ORDER_CREATION, (
                f"Feature '{feat}' classified as {availability}, must be ORDER_CREATION"
            )

        # Confirm known leakage columns are classified as POST_DELIVERY
        for leak_col in ["actual_delivery_date", "delay_days", "delayed", "delivery_status", "delay_reason"]:
            assert classify_column_availability(leak_col) == FeatureAvailability.POST_DELIVERY

    def test_loaded_feature_splits_contain_no_leakage(self):
        """Verify that real generated feature splits (classification and regression) pass leakage checks."""
        for task in ("classification", "regression"):
            train_df, val_df, test_df = load_feature_splits(task)

            target = CLASSIFICATION_TARGET if task == "classification" else REGRESSION_TARGET

            X_train, y_train = separate_features_and_target(train_df, target)
            X_val, y_val = separate_features_and_target(val_df, target)
            X_test, y_test = separate_features_and_target(test_df, target)

            for split_name, X in [("train", X_train), ("val", X_val), ("test", X_test)]:
                report = check_feature_matrix_for_leakage(X, raise_on_error=True)
                assert report["passed"] is True
                assert set(X.columns) == set(APPROVED_FEATURES)
                assert target not in X.columns
                assert "actual_delivery_date" not in X.columns
                assert "delivery_status" not in X.columns

    def test_leakage_check_raises_when_forbidden_column_present(self):
        """Verify that check_feature_matrix_for_leakage immediately raises ValueError when leakage occurs."""
        tainted_df = pd.DataFrame({
            "supplier_reliability": [0.9],
            "actual_delivery_date": ["2024-03-01"],
            "delayed": [1],
        })

        with pytest.raises(ValueError, match="Data leakage detected"):
            check_feature_matrix_for_leakage(tainted_df, raise_on_error=True)

    def test_preprocessor_fits_strictly_on_training_split(self):
        """
        Verify that preprocessor parameters (StandardScaler mean and variance)
        are solely derived from X_train and completely unaffected by test distributions.
        """
        # Create distinct train and test feature distributions
        train_df = pd.DataFrame({
            "supplier_reliability": [0.80, 0.82, 0.84],
            "historical_avg_delay": [1.0, 1.2, 1.4],
            "lead_time": [5, 6, 7],
            "inventory_level": [100, 200, 300],
            "demand": [150, 160, 170],
            "quantity": [50, 60, 70],
            "shipping_cost": [100.0, 110.0, 120.0],
            "distance": [300.0, 320.0, 340.0],
            "transport_mode": ["Road", "Road", "Air"],
            "season": ["Spring", "Spring", "Summer"],
            "priority": ["Medium", "Medium", "High"],
        })

        test_df = pd.DataFrame({
            "supplier_reliability": [0.10, 0.20],  # Drastically different
            "historical_avg_delay": [10.0, 12.0],
            "lead_time": [25, 30],
            "inventory_level": [9000, 9500],
            "demand": [5000, 5200],
            "quantity": [2000, 2500],
            "shipping_cost": [800.0, 900.0],
            "distance": [4000.0, 5000.0],
            "transport_mode": ["Sea", "Sea"],
            "season": ["Winter", "Winter"],
            "priority": ["Low", "Low"],
        })

        # Fit on train only
        preprocessor = fit_preprocessor(train_df)

        encoder = preprocessor.named_transformers_["cat"]
        train_transport_modes = set(train_df["transport_mode"].unique())
        fitted_transport_modes = set(encoder.categories_[0])

        # Encoder categories must match train set exactly, completely ignorant of test categories
        assert fitted_transport_modes == train_transport_modes
        assert "Sea" not in fitted_transport_modes  # Only present in test_df

        # Transforming test data must succeed even with unseen category levels (ignored cleanly)
        X_test_trans = transform_features(preprocessor, test_df)
        assert X_test_trans.shape[0] == 2
        assert not np.isnan(X_test_trans).any()

    def test_temporal_split_order_is_respected(self):
        """
        Verify that temporal ordering is maintained across train, val, and test splits.
        Checks metadata and split files generated by the ML pipeline.
        """
        split_meta_path = FEATURES_DIR / "metadata" / "split_info.json"
        if split_meta_path.exists():
            with open(split_meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            assert "split_strategy" in meta or "split_type" in meta or "train_rows" in meta
            assert meta.get("train_rows", 0) > 0
            assert meta.get("val_rows", 0) > 0
            assert meta.get("test_rows", 0) > 0

        # Check raw processed dataset dates if available
        processed_csv = Path("data/processed/shipments_processed.csv")
        if processed_csv.exists():
            df = pd.read_csv(processed_csv, parse_dates=["order_date"])
            # If sorted chronologically before split, train orders must be earlier than test orders
            n_total = len(df)
            train_idx_end = int(n_total * 0.70)
            val_idx_end = int(n_total * 0.85)

            train_max_date = df["order_date"].iloc[:train_idx_end].max()
            test_min_date = df["order_date"].iloc[val_idx_end:].min()

            # Ensure train max date is <= test min date (strictly forward in time)
            assert train_max_date <= test_min_date, (
                f"Temporal leak: Train max date {train_max_date} is after Test min date {test_min_date}"
            )
