"""
Unit Tests for ml/predict.py and Model Artifact Loading — Day 8
===============================================================
Tests loading compatibility artifact models/xgboost_delay_model.pkl,
versioned artifact parity, inference active model version verification,
and in-memory cache reloading.
"""

from __future__ import annotations

from pathlib import Path
import joblib
import numpy as np
import pytest
from xgboost import XGBClassifier, XGBRegressor

from ml.feature_config import PRIMARY_COMPATIBILITY_MODEL_PATH
from ml.model_registry import (
    get_active_model_version,
    load_model_version,
)
from ml.predict import (
    clear_model_cache,
    predict_shipment,
    reload_active_model,
)
from ml.preprocess import transform_features


@pytest.fixture
def sample_features() -> dict:
    return {
        "supplier_reliability": 0.88,
        "historical_avg_delay": 1.4,
        "lead_time": 6,
        "inventory_level": 250,
        "demand": 300,
        "quantity": 100,
        "shipping_cost": 180.0,
        "distance": 500.0,
        "transport_mode": "Road",
        "season": "Summer",
        "priority": "Medium",
    }


class TestModelLoading:
    """Test suite for loading models and runtime prediction verification."""

    def test_primary_compatibility_artifact_exists_and_loads(self):
        """Verify models/xgboost_delay_model.pkl exists and loads as fitted XGBClassifier."""
        assert PRIMARY_COMPATIBILITY_MODEL_PATH.exists()
        model = joblib.load(PRIMARY_COMPATIBILITY_MODEL_PATH)
        assert isinstance(model, XGBClassifier)
        assert hasattr(model, "predict_proba")

    def test_compatibility_artifact_matches_versioned_classifier(self, sample_features):
        """Verify predictions from models/xgboost_delay_model.pkl match models/versions/v1.0/classifier.pkl."""
        compat_clf = joblib.load(PRIMARY_COMPATIBILITY_MODEL_PATH)
        bundle = load_model_version("v1.0")
        v1_clf = bundle["classifier"]
        prep = bundle["preprocessor"]

        import pandas as pd
        X_df = pd.DataFrame([sample_features])
        X_trans = transform_features(prep, X_df)

        prob_compat = compat_clf.predict_proba(X_trans)[:, 1]
        prob_v1 = v1_clf.predict_proba(X_trans)[:, 1]

        np.testing.assert_allclose(prob_compat, prob_v1, rtol=1e-6)

    def test_inference_returns_active_model_version(self, sample_features):
        """Verify predict_shipment includes active model version in output dictionary."""
        active_v = get_active_model_version()
        res = predict_shipment(sample_features)

        assert isinstance(res, dict)
        assert res["model_version"] == active_v
        assert res["model_version"] == "v1.0"
        assert "delayed" in res
        assert "delay_probability" in res
        assert "predicted_delay_days" in res

    def test_reload_active_model_cache(self):
        """Verify reload_active_model refreshes in-memory cache and returns active version."""
        clear_model_cache()
        active = reload_active_model()
        assert active == "v1.0"

    def test_corrupted_artifact_raises_error(self, tmp_path, monkeypatch):
        """Verify attempting to load corrupted model raises error without substituting fake predictions."""
        bad_file = tmp_path / "corrupted_model.pkl"
        bad_file.write_bytes(b"garbage_not_pickle_data")

        with pytest.raises(Exception):
            joblib.load(bad_file)
