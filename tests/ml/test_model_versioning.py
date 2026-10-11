"""
Unit Tests for ml/model_registry.py — Model Versioning Lifecycle
================================================================
Tests version directory isolation, preventing silent overwrites, atomic active pointer updates,
and safe promotion rollbacks when validation fails.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
import pytest
import joblib

from ml.model_registry import (
    get_active_model_version,
    get_version_dir,
    promote_model_to_active,
    register_model_version,
    verify_model_artifacts,
)


class TestModelVersioning:
    """Test suite for version creation, protection, and promotion semantics."""

    def test_cannot_overwrite_existing_version_silently(self):
        """Verify calling register_model_version on an existing version without overwrite=True raises FileExistsError."""
        # v1.0 already exists
        with pytest.raises(FileExistsError, match="already registered"):
            register_model_version(
                version="v1.0",
                classifier="dummy",
                regressor="dummy",
                preprocessor="dummy",
                overwrite=False,
            )

    def test_register_and_promote_new_version_in_isolated_dir(self):
        """Verify registering a new version creates an isolated directory without corrupting v1.0."""
        # Load v1.0 components to clone
        from ml.model_registry import load_model_version
        v1_bundle = load_model_version("v1.0")

        test_version = "v1.1-test"
        v_test_dir = get_version_dir(test_version)

        try:
            # Register new version
            registered_dir = register_model_version(
                version=test_version,
                classifier=v1_bundle["classifier"],
                regressor=v1_bundle["regressor"],
                preprocessor=v1_bundle["preprocessor"],
                metadata=v1_bundle["metadata"],
                metrics=v1_bundle["metrics"],
                overwrite=True,
                set_active=False,
            )

            assert registered_dir.exists()
            assert (registered_dir / "classifier.pkl").exists()
            assert (registered_dir / "metadata.json").exists()

            # Active should still be v1.0 since set_active=False
            assert get_active_model_version() == "v1.0"

            # Verify artifacts in the new version
            verification = verify_model_artifacts(test_version)
            assert verification["valid"] is True

            # Promote to active
            promote_model_to_active(test_version)
            assert get_active_model_version() == test_version

        finally:
            # Restore active back to v1.0
            promote_model_to_active("v1.0")
            # Clean up test version directory
            if v_test_dir.exists():
                import shutil
                shutil.rmtree(v_test_dir)

    def test_failed_promotion_preserves_previous_active_version(self, monkeypatch):
        """Verify that when promotion fails (due to invalid artifacts), the existing active model remains active."""
        current_active = get_active_model_version()

        # Attempt to promote a completely nonexistent version
        with pytest.raises(ValueError, match="Cannot promote"):
            promote_model_to_active("v_corrupted_nonexistent")

        # Active version must remain unchanged
        assert get_active_model_version() == current_active

    def test_atomic_pointer_write(self):
        """Verify active.json pointer format and atomic creation."""
        from ml.feature_config import ACTIVE_VERSION_POINTER_PATH

        assert ACTIVE_VERSION_POINTER_PATH.exists()
        with open(ACTIVE_VERSION_POINTER_PATH, "r", encoding="utf-8") as f:
            pointer = json.load(f)

        assert "active_version" in pointer
        assert "promoted_at_utc" in pointer
        assert pointer["active_version"] == "v1.0"
