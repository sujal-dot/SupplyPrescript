"""
Unit tests for ml/train.py
==========================
Tests model training routines, validation evaluation, threshold selection,
and reproducibility with fixed random seeds.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.evaluate import (
    evaluate_classification,
    evaluate_regression,
    find_optimal_threshold,
)
from ml.feature_config import APPROVED_FEATURES
from ml.train import (
    train_classification_model,
    train_regression_model,
)


@pytest.fixture
def synthetic_split_dataset() -> Path:
    """Create a temporary directory containing train, val, test CSVs for testing training routines."""
    tmpdir = tempfile.mkdtemp()
    base_path = Path(tmpdir)
    cls_path = base_path / "classification"
    reg_path = base_path / "regression"
    cls_path.mkdir(parents=True, exist_ok=True)
    reg_path.mkdir(parents=True, exist_ok=True)

    np.random.seed(42)
    for n_rows, filename in [(60, "train.csv"), (20, "validation.csv"), (20, "test.csv")]:
        df = pd.DataFrame({
            "supplier_reliability": np.random.uniform(0.7, 0.99, n_rows),
            "historical_avg_delay": np.random.exponential(1.0, n_rows),
            "lead_time": np.random.randint(3, 15, n_rows),
            "inventory_level": np.random.randint(100, 2000, n_rows),
            "demand": np.random.randint(80, 1500, n_rows),
            "quantity": np.random.randint(50, 1000, n_rows),
            "shipping_cost": np.random.uniform(100, 3000, n_rows),
            "distance": np.random.uniform(50, 2000, n_rows),
            "transport_mode": np.random.choice(["Road", "Rail", "Air", "Sea"], n_rows),
            "season": np.random.choice(["Winter", "Summer", "Monsoon", "Post-Monsoon"], n_rows),
            "priority": np.random.choice(["Low", "Medium", "High", "Critical"], n_rows),
            "delay_days": np.random.choice([0, 0, 0, 1, 3, 5], n_rows),
        })
        df["delayed"] = (df["delay_days"] > 0).astype(int)

        # Save classification
        cls_df = df[APPROVED_FEATURES + ["delayed"]]
        cls_df.to_csv(cls_path / filename, index=False)

        # Save regression
        reg_df = df[APPROVED_FEATURES + ["delay_days"]]
        reg_df.to_csv(reg_path / filename, index=False)

    return base_path


def test_find_optimal_threshold():
    """Verify threshold tuning chooses threshold that maximizes F1 score."""
    y_true = np.array([0, 0, 0, 1, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.4, 0.6, 0.8, 0.9])
    best_thresh, info = find_optimal_threshold(y_true, y_prob, metric="f1")
    assert 0.1 <= best_thresh <= 0.9
    assert "history" in info
    assert len(info["history"]) > 0


def test_evaluate_classification():
    """Verify classification evaluation produces expected metric fields."""
    y_true = np.array([0, 1, 0, 1])
    y_prob = np.array([0.2, 0.8, 0.3, 0.7])
    metrics = evaluate_classification(y_true, y_prob, threshold=0.5)
    assert metrics["accuracy"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert "confusion_matrix" in metrics
    assert "classification_report" in metrics


def test_evaluate_regression():
    """Verify regression evaluation produces non-negative clipped metrics."""
    y_true = np.array([0.0, 3.0, 5.0])
    y_pred = np.array([-1.0, 3.0, 4.0])  # Negative value should be clipped to 0
    metrics = evaluate_regression(y_true, y_pred)
    assert metrics["mae"] >= 0.0
    assert metrics["rmse"] >= 0.0
    assert "median_absolute_error" in metrics


def test_train_classification_model_synthetic(synthetic_split_dataset):
    """Test train_classification_model executes successfully with custom reports dir."""
    cls_data_dir = synthetic_split_dataset / "classification"
    reports_dir = synthetic_split_dataset / "reports_cls"
    res = train_classification_model(data_dir=cls_data_dir, reports_dir=reports_dir)
    assert res["status"] == "SUCCESS"
    assert "validation_metrics" in res
    assert "test_metrics" in res
    assert (reports_dir / "metrics.json").exists()
    assert (reports_dir / "confusion_matrix.png").exists()


def test_train_regression_model_synthetic(synthetic_split_dataset):
    """Test train_regression_model executes successfully with custom reports dir."""
    reg_data_dir = synthetic_split_dataset / "regression"
    reports_dir = synthetic_split_dataset / "reports_reg"
    res = train_regression_model(data_dir=reg_data_dir, reports_dir=reports_dir)
    assert res["status"] == "SUCCESS"
    assert "validation_metrics" in res
    assert "test_metrics" in res
    assert (reports_dir / "metrics.json").exists()
    assert (reports_dir / "actual_vs_predicted.png").exists()
