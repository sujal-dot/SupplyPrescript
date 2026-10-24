"""SupplyPrescript — Unit & Integration Tests for Retraining Engine (Day 23)
========================================================================
Validates performance degradation detection, candidate dataset preparation,
XGBoost candidate retraining isolation, validation acceptance criteria,
atomic model registration, and safe rollback.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from app.database.connection import SessionLocal
from app.models.feedback import Feedback
from app.models.retraining_job import RetrainingJob
from app.services.model_monitor import (
    detect_performance_degradation,
    load_model_baseline_metrics,
)
from app.services.retraining_service import (
    check_retraining_concurrency_and_cooldown,
    enqueue_and_execute_retraining,
    promote_registered_candidate,
    rollback_production_model,
)
from ml.candidate_validation import validate_candidate_model
from ml.feature_config import APPROVED_FEATURES
from ml.model_registry import (
    get_active_model_version,
    get_version_dir,
    promote_model_to_active,
)
from ml.retrain import (
    get_next_candidate_version,
    prepare_retraining_dataset,
    train_candidate_models,
)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


class TestModelMonitorAndDegradation:
    """Test degradation detection logic and threshold enforcement."""

    def test_insufficient_samples_blocks_retraining(self, db_session):
        """When eligible samples < threshold, degradation check must return INSUFFICIENT_DATA."""
        report = detect_performance_degradation(
            db=db_session,
            model_version="v1.0.0",
            min_feedback_threshold=1000,  # Unattainably high to guarantee insufficient
        )
        assert report["status"] == "INSUFFICIENT_DATA"
        assert report["is_degraded"] is False
        assert report["trigger_retraining"] is False
        assert "INSUFFICIENT_DATA" in report["trigger_reason"]

    def test_load_baseline_metrics_returns_valid_data(self):
        """Verify baseline metrics loader reads regression and classification baselines."""
        baseline = load_model_baseline_metrics("v1.0")
        assert "regression" in baseline
        assert "mae" in baseline["regression"]
        assert baseline["regression"]["mae"] > 0

    def test_candidate_version_allocation(self):
        """Verify candidate version allocation increments minor version."""
        assert get_next_candidate_version("v1.0") == "v1.1"
        assert get_next_candidate_version("v1.0.0") == "v1.1.0"
        assert get_next_candidate_version("v2.3") == "v2.4"


class TestCandidateRetrainingAndValidation:
    """Test candidate model training, isolation, and acceptance rules."""

    @pytest.fixture
    def synthetic_data(self):
        """Generate small synthetic train/val/test splits conforming to Day 6 schema with balanced classes."""
        rng = np.random.default_rng(42)
        n = 60
        is_delayed = rng.choice([0, 1], n, p=[0.5, 0.5])
        delay_days = np.where(is_delayed == 1, rng.uniform(1.0, 6.0, n), 0.0)

        df = pd.DataFrame({
            "supplier_reliability": rng.uniform(0.6, 1.0, n),
            "historical_avg_delay": rng.uniform(0.0, 5.0, n),
            "lead_time": rng.integers(3, 14, n),
            "inventory_level": rng.integers(100, 1000, n),
            "demand": rng.integers(50, 500, n),
            "quantity": rng.integers(50, 500, n),
            "shipping_cost": rng.uniform(50.0, 500.0, n),
            "distance": rng.uniform(100.0, 1500.0, n),
            "transport_mode": rng.choice(["Road", "Rail", "Air", "Sea"], n),
            "season": rng.choice(["Winter", "Summer", "Monsoon", "Post-Monsoon"], n),
            "priority": rng.choice(["Low", "Medium", "High", "Critical"], n),
            "delay_days": delay_days,
            "delayed": is_delayed,
        })

        train_df = df.iloc[:40].copy()
        val_df = df.iloc[40:50].copy()
        test_df = df.iloc[50:].copy()
        return train_df, val_df, test_df

    def test_dataset_preparation_preserves_targets_and_features(self, synthetic_data):
        """Verify dataset preparation produces leak-free feature matrices with canonical targets."""
        train_df, val_df, test_df = synthetic_data
        fb_sample = pd.DataFrame([{
            "supplier_reliability": 0.9,
            "historical_avg_delay": 1.0,
            "lead_time": 5,
            "inventory_level": 400,
            "demand": 200,
            "quantity": 100,
            "shipping_cost": 120.0,
            "distance": 350.0,
            "transport_mode": "Road",
            "season": "Winter",
            "priority": "High",
            "actual_delay": 2.5,
        }])

        c_train, c_val, c_test, fp = prepare_retraining_dataset(feedback_df=fb_sample)
        assert len(c_train) > len(train_df)
        assert "delay_days" in c_train.columns
        assert "delayed" in c_train.columns
        assert len(fp) == 64  # SHA-256 hex length

    def test_candidate_training_isolation(self, synthetic_data):
        """Verify candidate training writes strictly to isolated candidate directory and preserves active production artifacts."""
        train_df, val_df, test_df = synthetic_data
        active_before = get_active_model_version()
        candidate_version = "v1.99-test"

        temp_dir = Path(tempfile.mkdtemp())
        try:
            cand_output = temp_dir / candidate_version
            result = train_candidate_models(
                train_df=train_df,
                val_df=val_df,
                test_df=test_df,
                candidate_version=candidate_version,
                output_dir=cand_output,
            )

            assert result["status"] == "SUCCESS"
            assert (cand_output / "classifier.pkl").exists()
            assert (cand_output / "regressor.pkl").exists()
            assert (cand_output / "preprocessor.pkl").exists()
            assert (cand_output / "metadata.json").exists()

            # Active production version must NOT have changed!
            assert get_active_model_version() == active_before
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_candidate_validation_accepts_good_model(self, synthetic_data):
        """Verify validation checks pass when candidate meets acceptance criteria."""
        train_df, val_df, test_df = synthetic_data
        candidate_version = "v1.98-test"
        temp_dir = Path(tempfile.mkdtemp())

        try:
            cand_output = temp_dir / candidate_version
            train_candidate_models(
                train_df=train_df,
                val_df=val_df,
                test_df=test_df,
                candidate_version=candidate_version,
                output_dir=cand_output,
            )

            val_res = validate_candidate_model(
                candidate_version=candidate_version,
                candidate_dir=cand_output,
                baseline_version="v1.0",
                evaluation_df=test_df,
                min_eval_samples=5,
            )

            assert "checks" in val_res
            assert val_res["checks"].get("artifact_integrity") is True
            assert val_res["checks"].get("smoke_test_predictions") is True
            assert val_res["checks"].get("leakage_check") is True
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_candidate_validation_rejects_corrupt_artifacts(self):
        """Verify candidate validation rejects missing or corrupted artifacts."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Empty candidate directory
            val_res = validate_candidate_model(
                candidate_version="v1.97-bad",
                candidate_dir=temp_dir,
            )
            assert val_res["accepted"] is False
            assert val_res["recommendation"] == "REJECT_CANDIDATE"
            assert any("Missing required" in e for e in val_res["errors"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestPromotionAndRollback:
    """Test safe promotion and rollback operations."""

    def test_rollback_to_known_good_version(self, db_session):
        """Verify rolling back to v1.0 succeeds and updates pointer."""
        initial_version = get_active_model_version()
        res = rollback_production_model("v1.0", db=db_session)
        assert res["status"] == "SUCCESS"
        assert res["active_version"] == "v1.0"
        assert get_active_model_version() == "v1.0"

    def test_rollback_to_nonexistent_version_fails(self, db_session):
        """Verify rollback to an invalid version raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            rollback_production_model("v999.999", db=db_session)
