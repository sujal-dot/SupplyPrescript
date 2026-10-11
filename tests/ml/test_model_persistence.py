"""
Tests for ML Model Persistence and Registry
============================================
Verifies serialization, reloading, metadata schema consistency, and prediction
invariance across disk cycles for classification and regression models.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from xgboost import XGBClassifier, XGBRegressor

from ml.feature_config import (
    APPROVED_FEATURES,
    CLASSIFICATION_ARTIFACTS_DIR,
    REGRESSION_ARTIFACTS_DIR,
)
from ml.model_registry import (
    compute_file_fingerprint,
    get_artifact_directory,
    load_registered_model,
    save_registered_model,
)
from ml.preprocess import fit_preprocessor, transform_features


@pytest.fixture
def sample_feature_df() -> pd.DataFrame:
    """Provide a minimal valid feature dataframe matching approved features."""
    return pd.DataFrame({
        "supplier_reliability": [0.85, 0.40, 0.95],
        "historical_avg_delay": [1.5, 4.2, 0.2],
        "lead_time": [7, 14, 5],
        "inventory_level": [300, 50, 800],
        "demand": [250, 120, 700],
        "quantity": [100, 20, 500],
        "shipping_cost": [150.0, 45.0, 320.0],
        "distance": [450.0, 1200.0, 210.0],
        "transport_mode": ["Air", "Sea", "Road"],
        "season": ["Winter", "Summer", "Spring"],
        "priority": ["High", "Low", "Medium"],
    })


class TestModelPersistence:
    """Test suite for model artifact serialization, deserialization, and registry."""

    def test_registered_artifacts_exist_on_disk(self):
        """Verify that pre-trained artifacts exist in both artifact directories."""
        for task, art_dir in [("classification", CLASSIFICATION_ARTIFACTS_DIR), ("regression", REGRESSION_ARTIFACTS_DIR)]:
            assert art_dir.exists(), f"Artifact directory {art_dir} should exist"
            assert (art_dir / "model.joblib").exists(), f"model.joblib missing in {art_dir}"
            assert (art_dir / "preprocessor.joblib").exists(), f"preprocessor.joblib missing in {art_dir}"
            assert (art_dir / "metadata.json").exists(), f"metadata.json missing in {art_dir}"

    def test_load_classification_model_and_preprocessor(self):
        """Verify loading the production classification model and its components."""
        model, preprocessor, metadata = load_registered_model("classification")
        assert isinstance(model, XGBClassifier)
        assert preprocessor is not None
        assert hasattr(preprocessor, "transform")
        assert metadata["task"] == "classification"
        assert metadata["model_version"] == "1.0.0"

    def test_load_regression_model_and_preprocessor(self):
        """Verify loading the production regression model and its components."""
        model, preprocessor, metadata = load_registered_model("regression")
        assert isinstance(model, XGBRegressor)
        assert preprocessor is not None
        assert hasattr(preprocessor, "transform")
        assert metadata["task"] == "regression"
        assert metadata["model_version"] == "1.0.0"

    def test_metadata_schema_conformance(self):
        """Verify metadata.json contains all required audit and lineage keys."""
        for task in ("classification", "regression"):
            _, _, meta = load_registered_model(task)

            required_keys = [
                "model_name",
                "task",
                "model_type",
                "model_version",
                "trained_at_utc",
                "random_seed",
                "framework_versions",
                "features",
                "target",
                "dataset_tracking",
                "metrics",
                "artifact_paths",
            ]
            for key in required_keys:
                assert key in meta, f"Metadata for {task} missing required key '{key}'"

            # Check framework versions
            assert "xgboost" in meta["framework_versions"]
            assert "scikit_learn" in meta["framework_versions"]

            # Check feature names match approved features
            assert meta["features"]["feature_names"] == APPROVED_FEATURES
            assert meta["features"]["feature_count"] == len(APPROVED_FEATURES)

            # Check metrics structure
            assert "validation" in meta["metrics"]
            assert "test" in meta["metrics"]

    def test_saved_and_reloaded_model_prediction_identity(self, sample_feature_df):
        """Verify that serializing to disk and reloading yields byte-for-byte identical predictions."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Fit preprocessor on sample
            preprocessor = fit_preprocessor(sample_feature_df)
            X_trans = transform_features(preprocessor, sample_feature_df)

            # Train a tiny XGBClassifier
            clf = XGBClassifier(n_estimators=5, max_depth=2, random_state=42)
            y_dummy = np.array([1, 0, 1])
            clf.fit(X_trans, y_dummy)

            pred_prob_orig = clf.predict_proba(X_trans)[:, 1]

            # Save in custom dir
            import joblib
            model_file = tmp_path / "model.joblib"
            prep_file = tmp_path / "preprocessor.joblib"
            joblib.dump(clf, model_file)
            joblib.dump(preprocessor, prep_file)

            # Reload
            clf_loaded = joblib.load(model_file)
            prep_loaded = joblib.load(prep_file)

            X_trans_reloaded = transform_features(prep_loaded, sample_feature_df)
            pred_prob_reloaded = clf_loaded.predict_proba(X_trans_reloaded)[:, 1]

            np.testing.assert_allclose(pred_prob_orig, pred_prob_reloaded, rtol=1e-6)

    def test_unknown_task_raises_value_error(self):
        """Verify that passing an invalid task name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown task"):
            get_artifact_directory("reinforcement_learning")

        with pytest.raises(ValueError, match="Unknown task"):
            load_registered_model("invalid_task")

    def test_missing_artifacts_raises_file_not_found_error(self, monkeypatch):
        """Verify that missing files raise FileNotFoundError with descriptive message."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_path = Path(tmp_dir)
            # Patch get_artifact_directory to return empty directory
            monkeypatch.setattr("ml.model_registry.get_artifact_directory", lambda task: empty_path)

            with pytest.raises(FileNotFoundError, match="Model artifact for task"):
                load_registered_model("classification")

    def test_compute_file_fingerprint(self):
        """Verify fingerprint hashing utility."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test_content_for_hash")
            temp_path = Path(f.name)

        try:
            fp1 = compute_file_fingerprint(temp_path)
            assert isinstance(fp1, str)
            assert len(fp1) == 16

            fp2 = compute_file_fingerprint(temp_path)
            assert fp1 == fp2  # Deterministic

            # Missing file
            assert compute_file_fingerprint(Path("/nonexistent/path/file.txt")) == "not_found"
        finally:
            temp_path.unlink(missing_ok=True)
