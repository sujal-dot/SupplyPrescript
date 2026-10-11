"""
Unit Tests for ml/model_registry.py — Model Registry Operations
===============================================================
Tests listing versions, active version tracking, artifact verification,
tamper detection via SHA-256 checksums, and metadata schema.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import pytest
import joblib

from ml.model_registry import (
    compute_file_checksum,
    get_active_model_version,
    get_version_dir,
    list_model_versions,
    load_model_version,
    register_model_version,
    verify_model_artifacts,
)


class TestModelRegistry:
    """Test suite for model registry and verification."""

    def test_active_model_version_is_v1_0(self):
        """Verify the active model version is v1.0."""
        active = get_active_model_version()
        assert active == "v1.0"

    def test_list_model_versions_contains_v1_0(self):
        """Verify list_model_versions lists v1.0 and marks it active."""
        versions = list_model_versions()
        assert len(versions) >= 1
        v1_entries = [v for v in versions if v["version"] == "v1.0"]
        assert len(v1_entries) == 1
        v1 = v1_entries[0]
        assert v1["is_active"] is True
        assert v1["classifier"] == "XGBClassifier"
        assert v1["regressor"] == "XGBRegressor"

    def test_load_active_model_version(self):
        """Verify loading the active model bundle returns fitted estimators and metadata."""
        bundle = load_model_version()
        assert bundle["version"] == "v1.0"
        assert bundle["classifier"] is not None
        assert bundle["regressor"] is not None
        assert bundle["preprocessor"] is not None
        assert hasattr(bundle["classifier"], "predict_proba")
        assert hasattr(bundle["regressor"], "predict")
        assert hasattr(bundle["preprocessor"], "transform")
        assert "checksums" in bundle["metadata"]

    def test_verify_v1_0_artifacts_passes(self):
        """Verify artifact verification for production v1.0 succeeds."""
        res = verify_model_artifacts("v1.0")
        assert res["valid"] is True
        assert res["checksum_status"] == "passed"
        assert len(res["errors"]) == 0
        assert res["checksum_results"]["classifier.pkl"] is True
        assert res["checksum_results"]["regressor.pkl"] is True
        assert res["checksum_results"]["preprocessor.pkl"] is True

    def test_tampered_artifact_detected_by_checksum(self, monkeypatch):
        """Verify that altering a single byte in an artifact causes checksum verification failure."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_v_dir = Path(tmp_dir) / "v_test"
            test_v_dir.mkdir()

            # Create dummy model files
            clf_path = test_v_dir / "classifier.pkl"
            reg_path = test_v_dir / "regressor.pkl"
            prep_path = test_v_dir / "preprocessor.pkl"

            joblib.dump({"dummy": 1}, clf_path)
            joblib.dump({"dummy": 2}, reg_path)
            joblib.dump({"dummy": 3}, prep_path)

            correct_checksum = compute_file_checksum(clf_path)

            # Metadata with correct checksum
            meta = {
                "version": "v_test",
                "checksums": {
                    "classifier.pkl": correct_checksum,
                    "regressor.pkl": compute_file_checksum(reg_path),
                    "preprocessor.pkl": compute_file_checksum(prep_path),
                },
            }
            with open(test_v_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(meta, f)
            with open(test_v_dir / "metrics.json", "w", encoding="utf-8") as f:
                json.dump({}, f)

            # Patch get_version_dir to return this test directory
            monkeypatch.setattr("ml.model_registry.get_version_dir", lambda v: test_v_dir)

            # Now tamper with classifier.pkl
            with open(clf_path, "ab") as f:
                f.write(b"tamper_bytes_corruption")

            # Verification should fail
            res = verify_model_artifacts("v_test")
            assert res["valid"] is False
            assert res["checksum_status"] == "failed"
            assert any("Checksum mismatch" in err for err in res["errors"])

    def test_missing_artifact_files_detected(self, monkeypatch):
        """Verify missing files are detected and reported."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_v_dir = Path(tmp_dir) / "v_incomplete"
            test_v_dir.mkdir()
            # Only create metadata, missing models
            with open(test_v_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump({}, f)

            monkeypatch.setattr("ml.model_registry.get_version_dir", lambda v: test_v_dir)

            res = verify_model_artifacts("v_incomplete")
            assert res["valid"] is False
            assert any("missing" in err for err in res["errors"])

    def test_compute_file_checksum_errors(self):
        """Verify compute_file_checksum raises FileNotFoundError on missing file."""
        with pytest.raises(FileNotFoundError):
            compute_file_checksum(Path("/nonexistent/file/path.pkl"))
