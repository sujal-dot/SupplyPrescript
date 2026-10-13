"""
SupplyPrescript — Model Registry and Versioning System
======================================================
Manages production model versioning (starting at v1.0), SHA-256 artifact checksums,
metadata serialization, safe promotion verification, and atomic active-version tracking
for the dual XGBoost shipment delay prediction engine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost

from ml.feature_config import (
    ACTIVE_VERSION_POINTER_PATH,
    APPROVED_FEATURES,
    CLASSIFICATION_ARTIFACTS_DIR,
    CLASSIFICATION_TARGET,
    MODELS_ROOT_DIR,
    MODEL_VERSIONS_DIR,
    PRIMARY_COMPATIBILITY_MODEL_PATH,
    REGRESSION_ARTIFACTS_DIR,
    REGRESSION_TARGET,
)

logger = logging.getLogger("ml.model_registry")

DEFAULT_MODEL_VERSION = "v1.0"
PRIMARY_COMPATIBILITY_DOC = (
    "Primary delay prediction model artifact. Contains the production XGBClassifier "
    "trained to predict binary shipment delay risk. Serves as the canonical single-file "
    "delay model for SupplyPrescript. Dual-model components (regressor & preprocessor) "
    "are preserved in models/versions/."
)


# ---------------------------------------------------------------------------
# Checksum and Fingerprint Utilities
# ---------------------------------------------------------------------------
def compute_file_checksum(filepath: Union[str, Path]) -> str:
    """Compute complete SHA-256 hex checksum of a file for tamper detection."""
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"Cannot compute checksum; file does not exist: {p}")
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_file_fingerprint(filepath: Union[str, Path]) -> str:
    """Compute short 16-character SHA-256 fingerprint for quick reference."""
    p = Path(filepath)
    if not p.exists():
        return "not_found"
    return compute_file_checksum(p)[:16]


# ---------------------------------------------------------------------------
# Path Resolution and Active Pointer Helpers
# ---------------------------------------------------------------------------
def get_version_dir(version: str) -> Path:
    """Return root directory for a specific registered model version."""
    v_clean = version.strip()
    if not v_clean.startswith("v") and not v_clean.startswith("V"):
        v_clean = f"v{v_clean}"
    return MODEL_VERSIONS_DIR / v_clean.lower()


def get_active_model_version() -> str:
    """
    Return the active production model version string (e.g. 'v1.0').
    Falls back to 'v1.0' if pointer file is absent.
    """
    if ACTIVE_VERSION_POINTER_PATH.exists():
        try:
            with open(ACTIVE_VERSION_POINTER_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                active_v = data.get("active_version")
                if active_v:
                    return str(active_v)
        except Exception as e:
            logger.warning("Failed to read active version pointer (%s); using default.", e)

    # Fall back to latest registered directory or default
    versions = list_model_versions()
    if versions:
        return versions[0]["version"]
    return DEFAULT_MODEL_VERSION


def get_artifact_directory(task: str) -> Path:
    """Return task directory in ml/artifacts/ (legacy Day 7 compatibility)."""
    task_clean = task.strip().lower()
    if task_clean in ("classification", "cls"):
        return CLASSIFICATION_ARTIFACTS_DIR
    elif task_clean in ("regression", "reg"):
        return REGRESSION_ARTIFACTS_DIR
    else:
        raise ValueError(f"Unknown task '{task}'. Expected 'classification' or 'regression'.")


# ---------------------------------------------------------------------------
# Model Registration
# ---------------------------------------------------------------------------
def register_model_version(
    version: str = DEFAULT_MODEL_VERSION,
    classifier: Any = None,
    regressor: Any = None,
    preprocessor: Any = None,
    metadata: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    overwrite: bool = False,
    set_active: bool = False,
    dataset_path: Optional[Path] = None,
    train_row_count: int = 10500,
    val_row_count: int = 2250,
    test_row_count: int = 2250,
) -> Path:
    """
    Register a complete model version package in models/versions/{version}/.
    Stores classifier.pkl, regressor.pkl, preprocessor.pkl, metadata.json, and metrics.json.
    """
    v_dir = get_version_dir(version)
    canonical_version = v_dir.name

    if v_dir.exists() and not overwrite:
        raise FileExistsError(
            f"Model version '{canonical_version}' is already registered at {v_dir}. "
            "To overwrite an existing version, set overwrite=True."
        )

    v_dir.mkdir(parents=True, exist_ok=True)
    MODELS_ROOT_DIR.mkdir(parents=True, exist_ok=True)

    clf_path = v_dir / "classifier.pkl"
    reg_path = v_dir / "regressor.pkl"
    prep_path = v_dir / "preprocessor.pkl"
    meta_path = v_dir / "metadata.json"
    metrics_path = v_dir / "metrics.json"

    # Serialize artifacts
    joblib.dump(classifier, clf_path)
    joblib.dump(regressor, reg_path)
    joblib.dump(preprocessor, prep_path)

    # Compute checksums
    checksums = {
        "classifier.pkl": compute_file_checksum(clf_path),
        "regressor.pkl": compute_file_checksum(reg_path),
        "preprocessor.pkl": compute_file_checksum(prep_path),
    }

    dataset_fingerprint = compute_file_checksum(dataset_path) if dataset_path and Path(dataset_path).exists() else "unknown"

    now_utc = datetime.now(timezone.utc).isoformat()
    meta = metadata.copy() if metadata else {}
    mets = metrics.copy() if metrics else {}

    full_metadata: Dict[str, Any] = {
        "version": canonical_version,
        "model_name": "supplyprescript_delay_engine",
        "model_types": {
            "classifier": type(classifier).__name__,
            "regressor": type(regressor).__name__,
        },
        "registered_at_utc": now_utc,
        "training_timestamp_utc": meta.get("trained_at_utc", now_utc),
        "evaluation_timestamp_utc": now_utc,
        "random_seed": meta.get("random_seed", 42),
        "framework_versions": {
            "python": sys.version.split()[0],
            "xgboost": xgboost.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
        "features": {
            "feature_names": APPROVED_FEATURES,
            "feature_count": len(APPROVED_FEATURES),
            "transformed_feature_names": (
                __import__("ml.preprocess", fromlist=["get_transformed_feature_names"]).get_transformed_feature_names(preprocessor)
            ),
        },
        "targets": {
            "classification": CLASSIFICATION_TARGET,
            "regression": REGRESSION_TARGET,
        },
        "classification_threshold": meta.get("classification_threshold", 0.150),
        "dataset_tracking": {
            "source_path": str(dataset_path) if dataset_path else "data/processed/shipments_processed.csv",
            "fingerprint": dataset_fingerprint,
            "row_counts": {
                "train": train_row_count,
                "validation": val_row_count,
                "test": test_row_count,
                "total": train_row_count + val_row_count + test_row_count,
            },
        },
        "checksums": checksums,
        "artifacts": {
            "classifier": "classifier.pkl",
            "regressor": "regressor.pkl",
            "preprocessor": "preprocessor.pkl",
            "compatibility_model": "models/xgboost_delay_model.pkl",
        },
        "notes": (
            f"Release {canonical_version} for shipment delay intelligence. "
            "Classifier predicts probability of delay; Regressor estimates delay duration in days."
        ),
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(full_metadata, f, indent=2)

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(mets, f, indent=2)

    logger.info("Successfully registered model version '%s' at: %s", canonical_version, v_dir)

    # If first version or set_active requested, promote
    if set_active or not ACTIVE_VERSION_POINTER_PATH.exists():
        promote_model_to_active(canonical_version)

    return v_dir


# ---------------------------------------------------------------------------
# Verification and Safe Promotion
# ---------------------------------------------------------------------------
def verify_model_artifacts(version: str) -> Dict[str, Any]:
    """
    Thoroughly verify that all artifacts for a model version exist,
    match their recorded SHA-256 checksums, and pass a live smoke-test prediction.
    """
    v_dir = get_version_dir(version)
    errors: List[str] = []

    if not v_dir.exists():
        return {
            "valid": False,
            "version": version,
            "errors": [f"Version directory does not exist: {v_dir}"],
            "checksum_status": "missing_directory",
        }

    required_files = [
        "classifier.pkl",
        "regressor.pkl",
        "preprocessor.pkl",
        "metadata.json",
        "metrics.json",
    ]

    for fname in required_files:
        fpath = v_dir / fname
        if not fpath.exists():
            errors.append(f"Required artifact '{fname}' is missing in {v_dir}")

    if errors:
        return {"valid": False, "version": version, "errors": errors, "checksum_status": "missing_files"}

    # Validate metadata
    meta_path = v_dir / "metadata.json"
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Checksum validation
    recorded_checksums = metadata.get("checksums", {})
    checksum_results: Dict[str, bool] = {}
    for fname in ["classifier.pkl", "regressor.pkl", "preprocessor.pkl"]:
        actual_sum = compute_file_checksum(v_dir / fname)
        expected_sum = recorded_checksums.get(fname)
        if expected_sum != actual_sum:
            errors.append(
                f"Checksum mismatch for '{fname}'. Expected {expected_sum}, got {actual_sum}."
            )
            checksum_results[fname] = False
        else:
            checksum_results[fname] = True

    # Smoke test prediction
    try:
        clf = joblib.load(v_dir / "classifier.pkl")
        reg = joblib.load(v_dir / "regressor.pkl")
        prep = joblib.load(v_dir / "preprocessor.pkl")

        # Create dummy sample
        dummy_df = pd.DataFrame([{
            "supplier_reliability": 0.85,
            "historical_avg_delay": 1.2,
            "lead_time": 7,
            "inventory_level": 300,
            "demand": 250,
            "quantity": 100,
            "shipping_cost": 150.0,
            "distance": 450.0,
            "transport_mode": "Road",
            "season": "Winter",
            "priority": "High",
        }])

        from ml.preprocess import transform_features
        X_trans = transform_features(prep, dummy_df)
        prob = clf.predict_proba(X_trans)[:, 1]
        days = reg.predict(X_trans)

        if not (0.0 <= prob[0] <= 1.0):
            errors.append(f"Smoke test invalid probability output: {prob[0]}")
        if np.isnan(days[0]) or np.isinf(days[0]):
            errors.append(f"Smoke test invalid regression output: {days[0]}")

    except Exception as e:
        errors.append(f"Smoke test prediction failed with exception: {e}")

    valid = len(errors) == 0
    return {
        "valid": valid,
        "version": version,
        "errors": errors,
        "checksum_status": "passed" if valid else "failed",
        "checksum_results": checksum_results,
    }


def promote_model_to_active(version: str) -> bool:
    """
    Safely promote a registered version to active production status.
    Requires artifact verification and smoke test to pass before atomically
    updating the active pointer. If verification fails, preserves existing active version.
    """
    v_dir = get_version_dir(version)
    canonical_version = v_dir.name

    verification = verify_model_artifacts(canonical_version)
    if not verification["valid"]:
        err_msg = f"Cannot promote '{canonical_version}'; verification failed: {verification['errors']}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    # Atomic pointer update via temporary file + atomic rename
    MODEL_VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    previous_active = None
    if ACTIVE_VERSION_POINTER_PATH.exists():
        try:
            with open(ACTIVE_VERSION_POINTER_PATH, "r", encoding="utf-8") as f:
                previous_active = json.load(f).get("active_version")
        except Exception:
            pass

    pointer_data = {
        "active_version": canonical_version,
        "promoted_at_utc": datetime.now(timezone.utc).isoformat(),
        "previous_version": previous_active,
        "verified_checksums": verification["checksum_results"],
    }

    # Write atomically
    temp_pointer = ACTIVE_VERSION_POINTER_PATH.with_suffix(".tmp")
    with open(temp_pointer, "w", encoding="utf-8") as f:
        json.dump(pointer_data, f, indent=2)
    os.replace(temp_pointer, ACTIVE_VERSION_POINTER_PATH)

    # Update primary compatibility artifact models/xgboost_delay_model.pkl
    src_clf = v_dir / "classifier.pkl"
    if src_clf.exists():
        MODELS_ROOT_DIR.mkdir(parents=True, exist_ok=True)
        temp_comp = PRIMARY_COMPATIBILITY_MODEL_PATH.with_suffix(".tmp")
        shutil.copyfile(src_clf, temp_comp)
        os.replace(temp_comp, PRIMARY_COMPATIBILITY_MODEL_PATH)

    logger.info("Successfully promoted model version '%s' to active production.", canonical_version)
    return True


# ---------------------------------------------------------------------------
# Loading and Listing
# ---------------------------------------------------------------------------
def load_model_version(version: Optional[str] = None) -> Dict[str, Any]:
    """
    Load model components and metadata for a specified version or the active version.
    Returns: {
        "classifier": XGBClassifier,
        "regressor": XGBRegressor,
        "preprocessor": ColumnTransformer,
        "metadata": Dict,
        "metrics": Dict,
        "version": str,
    }
    """
    target_v = version or get_active_model_version()
    v_dir = get_version_dir(target_v)

    if not v_dir.exists():
        raise FileNotFoundError(f"Model version '{target_v}' not found at {v_dir}")

    clf_path = v_dir / "classifier.pkl"
    reg_path = v_dir / "regressor.pkl"
    prep_path = v_dir / "preprocessor.pkl"
    meta_path = v_dir / "metadata.json"
    metrics_path = v_dir / "metrics.json"

    for path, name in [(clf_path, "Classifier"), (reg_path, "Regressor"), (prep_path, "Preprocessor")]:
        if not path.exists():
            raise FileNotFoundError(f"{name} artifact missing in version '{target_v}' at: {path}")

    classifier = joblib.load(clf_path)
    regressor = joblib.load(reg_path)
    preprocessor = joblib.load(prep_path)

    metadata = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

    metrics = {}
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)

    return {
        "classifier": classifier,
        "regressor": regressor,
        "preprocessor": preprocessor,
        "metadata": metadata,
        "metrics": metrics,
        "version": v_dir.name,
    }


def list_model_versions() -> List[Dict[str, Any]]:
    """
    Enumerate all registered model versions in models/versions/ with status.
    """
    if not MODEL_VERSIONS_DIR.exists():
        return []

    active_v = None
    if ACTIVE_VERSION_POINTER_PATH.exists():
        try:
            with open(ACTIVE_VERSION_POINTER_PATH, "r", encoding="utf-8") as f:
                active_v = json.load(f).get("active_version")
        except Exception:
            pass

    versions_list: List[Dict[str, Any]] = []
    for item in sorted(MODEL_VERSIONS_DIR.iterdir()):
        if item.is_dir() and (item / "metadata.json").exists():
            try:
                with open(item / "metadata.json", "r", encoding="utf-8") as f:
                    meta = json.load(f)
                versions_list.append({
                    "version": item.name,
                    "is_active": (item.name == active_v),
                    "registered_at": meta.get("registered_at_utc"),
                    "classifier": meta.get("model_types", {}).get("classifier"),
                    "regressor": meta.get("model_types", {}).get("regressor"),
                    "path": str(item),
                })
            except Exception:
                continue

    return versions_list


# ---------------------------------------------------------------------------
# Backward Compatibility Helpers (Day 7 interface)
# ---------------------------------------------------------------------------
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
    version: str = "1.0.0",
    hyperparameters: Optional[Dict[str, Any]] = None,
) -> Path:
    """Save legacy single-task artifact to ml/artifacts/{task}/."""
    art_dir = get_artifact_directory(task)
    art_dir.mkdir(parents=True, exist_ok=True)

    model_path = art_dir / "model.joblib"
    preprocessor_path = art_dir / "preprocessor.joblib"
    metadata_path = art_dir / "metadata.json"

    joblib.dump(model, model_path)
    joblib.dump(preprocessor, preprocessor_path)

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

    return art_dir


def load_registered_model(task: str) -> Tuple[Any, Any, Dict[str, Any]]:
    """
    Load model, preprocessor, and metadata for a given task from ml/artifacts/{task}/.
    Preserves Day 7 task-specific artifact interface.
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


# ---------------------------------------------------------------------------
# CLI Management Entry Point
# ---------------------------------------------------------------------------
def main() -> None:
    """CLI management tool for model versioning and registry."""
    parser = argparse.ArgumentParser(description="SupplyPrescript Model Registry & Version Manager")
    parser.add_argument("--list", action="store_true", help="List all registered model versions")
    parser.add_argument("--active", action="store_true", help="Show currently active production version")
    parser.add_argument("--verify", type=str, metavar="VERSION", help="Verify artifacts and checksums for a version")
    parser.add_argument("--promote", type=str, metavar="VERSION", help="Safely promote a version to active production")

    args = parser.parse_args()

    if args.list:
        versions = list_model_versions()
        if not versions:
            print("No registered model versions found in models/versions/.")
            return
        print(f"\n{'Version':<10} {'Active':<8} {'Classifier':<16} {'Regressor':<16} {'Registered (UTC)':<24}")
        print("-" * 78)
        for v in versions:
            active_marker = "★ YES" if v["is_active"] else "  No"
            print(f"{v['version']:<10} {active_marker:<8} {str(v['classifier']):<16} {str(v['regressor']):<16} {str(v['registered_at']):<24}")
        print()

    elif args.active:
        active = get_active_model_version()
        print(f"Active production model version: {active}")

    elif args.verify:
        res = verify_model_artifacts(args.verify)
        print(f"\nVerification for version '{args.verify}': {'PASSED' if res['valid'] else 'FAILED'}")
        if res["errors"]:
            print("Errors detected:")
            for err in res["errors"]:
                print(f"  - {err}")
        else:
            print("  All artifact files, checksums, and smoke tests passed successfully.")
        print()

    elif args.promote:
        try:
            promote_model_to_active(args.promote)
            print(f"Successfully verified and promoted '{args.promote}' to active production.")
        except Exception as e:
            print(f"Promotion failed: {e}")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
