"""
SupplyPrescript — Model Registry and Artifact Management
========================================================
Manages versioning, metadata serialization, atomic artifact persistence,
and lifecycle retrieval for classification and regression delay models.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import sklearn
import xgboost

from ml.feature_config import (
    APPROVED_FEATURES,
    CLASSIFICATION_ARTIFACTS_DIR,
    CLASSIFICATION_TARGET,
    REGRESSION_ARTIFACTS_DIR,
    REGRESSION_TARGET,
)

logger = logging.getLogger("ml.model_registry")

DEFAULT_MODEL_VERSION = "1.0.0"


def compute_file_fingerprint(filepath: Path) -> str:
    """Compute SHA-256 fingerprint of a file for reproducibility tracking."""
    if not filepath.exists():
        return "not_found"
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()[:16]


def get_artifact_directory(task: str) -> Path:
    """Return root artifact directory for a given task."""
    task_clean = task.strip().lower()
    if task_clean in ("classification", "cls"):
        return CLASSIFICATION_ARTIFACTS_DIR
    elif task_clean in ("regression", "reg"):
        return REGRESSION_ARTIFACTS_DIR
    else:
        raise ValueError(f"Unknown task '{task}'. Expected 'classification' or 'regression'.")


def save_registered_model(
    model: Any,
    preprocessor: Any,
    task: str,
    validation_metrics: Dict[str, Any],
    test_metrics: Dict[str, Any],
    train_row_count: int,
    val_row_count: int,
    test_row_count: int,
    dataset_path: Optional[Path] = None,
    threshold: Optional[float] = None,
    version: str = DEFAULT_MODEL_VERSION,
    hyperparameters: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Save model, preprocessor, and comprehensive metadata into task artifact directory.
    """
    art_dir = get_artifact_directory(task)
    art_dir.mkdir(parents=True, exist_ok=True)

    model_path = art_dir / "model.joblib"
    preprocessor_path = art_dir / "preprocessor.joblib"
    metadata_path = art_dir / "metadata.json"

    # Serialize model and preprocessor
    joblib.dump(model, model_path)
    joblib.dump(preprocessor, preprocessor_path)

    # Compute dataset fingerprint if provided
    dataset_fingerprint = compute_file_fingerprint(dataset_path) if dataset_path else "unknown"

    target_name = CLASSIFICATION_TARGET if task in ("classification", "cls") else REGRESSION_TARGET
    model_type_name = type(model).__name__

    metadata: Dict[str, Any] = {
        "model_name": f"supplyprescript_{task}_{model_type_name.lower()}",
        "task": task,
        "model_type": model_type_name,
        "model_version": version,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "random_seed": 42,
        "framework_versions": {
            "xgboost": xgboost.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "features": {
            "feature_names": APPROVED_FEATURES,
            "feature_count": len(APPROVED_FEATURES),
            "transformed_feature_names": (
                list(preprocessor.get_feature_names_out())
                if hasattr(preprocessor, "get_feature_names_out")
                else []
            ),
        },
        "target": {
            "target_name": target_name,
            "classification_threshold": threshold if threshold is not None else (0.5 if task in ("classification", "cls") else None),
        },
        "dataset_tracking": {
            "source_path": str(dataset_path) if dataset_path else "default",
            "fingerprint": dataset_fingerprint,
            "row_counts": {
                "train": train_row_count,
                "validation": val_row_count,
                "test": test_row_count,
                "total": train_row_count + val_row_count + test_row_count,
            },
        },
        "hyperparameters": hyperparameters or {},
        "metrics": {
            "validation": validation_metrics,
            "test": test_metrics,
        },
        "artifact_paths": {
            "model": str(model_path),
            "preprocessor": str(preprocessor_path),
        },
    }

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Successfully registered '%s' model (version: %s) at: %s", task, version, art_dir)
    return art_dir


def load_registered_model(task: str) -> Tuple[Any, Any, Dict[str, Any]]:
    """
    Load model, preprocessor, and metadata for a given task.
    Returns: (model, preprocessor, metadata)
    """
    art_dir = get_artifact_directory(task)
    model_path = art_dir / "model.joblib"
    preprocessor_path = art_dir / "preprocessor.joblib"
    metadata_path = art_dir / "metadata.json"

    for path, name in [(model_path, "Model"), (preprocessor_path, "Preprocessor"), (metadata_path, "Metadata")]:
        if not path.exists():
            raise FileNotFoundError(f"{name} artifact for task '{task}' not found at: {path}")

    model = joblib.load(model_path)
    preprocessor = joblib.load(preprocessor_path)
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return model, preprocessor, metadata
