"""
Unit Tests for ml/evaluate.py — Day 8 Evaluation Suite
======================================================
Tests classification metrics (Accuracy, Precision, Recall, F1, ROC-AUC),
regression metrics (MAE, RMSE, R2, MedAE), edge cases (single class, constant target,
zero division), empty/invalid inputs, and report saving.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import numpy as np
import pytest

from ml.evaluate import (
    evaluate_classification,
    evaluate_regression,
    find_optimal_threshold,
    plot_classification_reports,
    plot_regression_reports,
    save_metrics_report,
)


class TestClassificationEvaluation:
    """Test suite for binary classification evaluation and edge cases."""

    def test_evaluate_classification_perfect_scores(self):
        """Verify metric values on a perfectly predicted toy dataset."""
        y_true = np.array([0, 0, 1, 1])
        y_prob = np.array([0.05, 0.15, 0.85, 0.95])

        metrics = evaluate_classification(y_true, y_prob, threshold=0.5)

        assert metrics["accuracy"] == 1.0
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1_score"] == 1.0
        assert metrics["roc_auc"] == 1.0
        assert metrics["pr_auc"] == 1.0
        assert metrics["sample_count"] == 4
        assert metrics["class_distribution"]["delayed_count"] == 2
        assert metrics["confusion_matrix"]["true_positives"] == 2
        assert metrics["confusion_matrix"]["true_negatives"] == 2

    def test_roc_auc_uses_continuous_probability_scores(self):
        """Verify ROC-AUC evaluates probability rankings rather than thresholded binary outputs."""
        y_true = np.array([0, 0, 1, 1])
        # Ranked correctly
        y_prob = np.array([0.2, 0.4, 0.6, 0.8])

        metrics = evaluate_classification(y_true, y_prob, threshold=0.9)  # High threshold
        # Despite accuracy dropping due to high threshold, ROC-AUC remains 1.0 because ranking is intact
        assert metrics["roc_auc"] == 1.0
        assert metrics["recall"] == 0.0  # Because threshold=0.9 predicted all 0

    def test_single_class_edge_case_handles_roc_auc_safely(self):
        """Verify that when only one class is present in test data, ROC-AUC is recorded as None with explanation."""
        y_true = np.array([0, 0, 0, 0])  # Only negative class
        y_prob = np.array([0.1, 0.2, 0.3, 0.4])

        metrics = evaluate_classification(y_true, y_prob, threshold=0.5)

        assert metrics["roc_auc"] is None
        assert metrics["roc_auc_reason"] is not None
        assert "only one class" in metrics["roc_auc_reason"].lower()
        assert metrics["accuracy"] == 1.0

    def test_zero_division_handled_safely(self):
        """Verify zero-division precision is 0.0 when model predicts no positive samples."""
        y_true = np.array([1, 1, 1])
        y_prob = np.array([0.1, 0.1, 0.1])  # Predicts zero positive cases at threshold 0.5

        metrics = evaluate_classification(y_true, y_prob, threshold=0.5)
        assert metrics["precision"] == 0.0
        assert metrics["recall"] == 0.0
        assert metrics["f1_score"] == 0.0

    def test_empty_dataset_raises_value_error(self):
        """Verify empty arrays raise clear ValueError."""
        with pytest.raises(ValueError, match="empty"):
            evaluate_classification([], [])

    def test_invalid_target_values_raise_value_error(self):
        """Verify non-binary target classes trigger ValueError."""
        with pytest.raises(ValueError, match="Invalid classification target value"):
            evaluate_classification([0, 1, 2], [0.1, 0.5, 0.9])

    def test_mismatched_lengths_raise_value_error(self):
        """Verify length mismatch between y_true and y_prob triggers ValueError."""
        with pytest.raises(ValueError, match="Shape mismatch"):
            evaluate_classification([0, 1], [0.5])


class TestRegressionEvaluation:
    """Test suite for continuous delay regression evaluation."""

    def test_evaluate_regression_known_values(self):
        """Verify MAE, RMSE, MedAE on known values."""
        y_true = np.array([2.0, 4.0, 6.0])
        y_pred = np.array([2.5, 3.5, 7.0])  # Errors: 0.5, -0.5, 1.0

        metrics = evaluate_regression(y_true, y_pred)

        # MAE: (0.5 + 0.5 + 1.0) / 3 = 0.6667
        assert np.isclose(metrics["mae"], 0.6667, atol=1e-3)
        # RMSE: sqrt((0.25 + 0.25 + 1.0)/3) = sqrt(0.5) = 0.7071
        assert np.isclose(metrics["rmse"], 0.7071, atol=1e-3)
        assert metrics["sample_count"] == 3
        assert metrics["r2_score"] is not None

    def test_non_negative_clipping_constraint(self):
        """Verify negative model predictions are strictly clipped to 0.0."""
        y_true = np.array([0.0, 1.0])
        y_pred = np.array([-3.5, 1.0])

        metrics = evaluate_regression(y_true, y_pred)

        # -3.5 is clipped to 0.0 -> error is |0.0 - 0.0| = 0.0, second is |1.0 - 1.0| = 0.0
        assert metrics["mae"] == 0.0
        assert metrics["rmse"] == 0.0

    def test_constant_target_r2_handling_safely(self):
        """Verify that constant target (zero variance) records R2 as None with explanation."""
        y_true = np.array([5.0, 5.0, 5.0])  # Zero variance
        y_pred = np.array([4.0, 5.0, 6.0])

        metrics = evaluate_regression(y_true, y_pred)

        assert metrics["r2_score"] is None
        assert metrics["r2_reason"] is not None
        assert "undefined" in metrics["r2_reason"].lower()

    def test_regression_empty_dataset_raises(self):
        """Verify empty arrays raise clear ValueError."""
        with pytest.raises(ValueError, match="empty"):
            evaluate_regression([], [])

    def test_regression_nan_values_raise(self):
        """Verify NaN target values trigger ValueError."""
        with pytest.raises(ValueError, match="NaN"):
            evaluate_regression([1.0, np.nan], [1.0, 2.0])


class TestEvaluationReportingAndPlots:
    """Test suite for artifact and plot generation."""

    def test_save_metrics_report_json(self):
        """Verify JSON metric serialization."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "test_metrics.json"
            data = {"accuracy": 0.85, "mae": 1.25}
            saved_path = save_metrics_report(data, out_file)

            assert saved_path.exists()
            with open(saved_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded == data

    def test_plot_generation(self):
        """Verify visual diagnostic plots are created on disk."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir)

            y_cls = np.array([0, 1, 0, 1, 1])
            y_prob = np.array([0.2, 0.8, 0.3, 0.7, 0.9])
            cls_plots = plot_classification_reports(y_cls, y_prob, out_dir, threshold=0.5)

            assert len(cls_plots) == 3
            for p in cls_plots:
                assert p.exists()
                assert p.stat().st_size > 1000

            y_reg = np.array([1.0, 2.5, 0.0, 4.0])
            y_pred = np.array([1.2, 2.1, 0.0, 3.8])
            reg_plots = plot_regression_reports(y_reg, y_pred, out_dir)

            assert len(reg_plots) == 2
            for p in reg_plots:
                assert p.exists()
                assert p.stat().st_size > 1000
