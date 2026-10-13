"""
SupplyPrescript — Machine Learning Preprocessing Module
=======================================================
Reusable preprocessing pipeline for loading feature splits, validating feature matrices,
fitting column transformers on training data only, and transforming features for model training
and inference without data leakage.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

from ml.feature_config import (
    APPROVED_FEATURES,
    CATEGORICAL_FEATURES,
    CLASSIFICATION_DIR,
    CLASSIFICATION_TARGET,
    NUMERICAL_FEATURES,
    REGRESSION_DIR,
    REGRESSION_TARGET,
)
from ml.feature_validation import (
    validate_categorical_features,
    validate_numerical_features,
    validate_targets,
)
from ml.leakage_checks import check_feature_matrix_for_leakage

logger = logging.getLogger("ml.preprocess")


def get_target_for_task(task: str) -> str:
    """Return canonical target column name for a given task or target alias."""
    task_clean = task.strip().lower()
    if task_clean in ("classification", "cls", CLASSIFICATION_TARGET.lower()):
        return CLASSIFICATION_TARGET
    elif task_clean in ("regression", "reg", REGRESSION_TARGET.lower()):
        return REGRESSION_TARGET
    else:
        raise ValueError(f"Unknown task '{task}'. Expected 'classification' or 'regression'.")


def get_task_directory(task: str) -> Path:
    """Return data features directory for a given task."""
    task_clean = task.strip().lower()
    if task_clean in ("classification", "cls"):
        return CLASSIFICATION_DIR
    elif task_clean in ("regression", "reg"):
        return REGRESSION_DIR
    else:
        raise ValueError(f"Unknown task '{task}'. Expected 'classification' or 'regression'.")


def load_feature_splits(
    task: str = "classification",
    custom_dir: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load train, validation, and test feature split datasets for a given task.
    Returns: (train_df, val_df, test_df)
    """
    data_dir = custom_dir or get_task_directory(task)
    train_path = data_dir / "train.csv"
    val_path = data_dir / "validation.csv"
    test_path = data_dir / "test.csv"

    for path, split_name in [(train_path, "Train"), (val_path, "Validation"), (test_path, "Test")]:
        if not path.exists():
            raise FileNotFoundError(f"{split_name} dataset not found at expected path: {path}")

    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)
    test_df = pd.read_csv(test_path)

    logger.info(
        "Loaded '%s' feature splits: train=%d, validation=%d, test=%d rows.",
        task, len(train_df), len(val_df), len(test_df),
    )
    return train_df, val_df, test_df


def separate_features_and_target(
    df: pd.DataFrame,
    task: str,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Separate input features from target column.
    Ensures target and other task targets are strictly removed from feature matrix X.
    """
    target_col = get_target_for_task(task)
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in DataFrame columns: {list(df.columns)}")

    y = df[target_col].copy()

    # Drop all target and post-delivery outcome columns from X
    leaky_targets = {target_col, CLASSIFICATION_TARGET, REGRESSION_TARGET, "is_delayed"}
    cols_to_drop = [c for c in leaky_targets if c in df.columns]
    X = df.drop(columns=cols_to_drop).copy()

    # If all approved features are present, keep only approved features
    if all(feat in X.columns for feat in APPROVED_FEATURES):
        X = X[APPROVED_FEATURES].copy()

    # Verify target is not in X
    if target_col in X.columns:
        raise ValueError(f"Target column '{target_col}' leaked into feature matrix X!")

    return X, y


def validate_feature_data(
    df: pd.DataFrame,
    task: Optional[str] = None,
    raise_on_error: bool = True,
) -> Dict[str, Any]:
    """
    Validate that DataFrame contains required features, no NaNs/inf, and valid targets if present.
    """
    missing_features = [f for f in APPROVED_FEATURES if f not in df.columns]
    if missing_features:
        msg = f"Missing required features: {missing_features}"
        if raise_on_error:
            raise ValueError(msg)
        return {"valid": False, "errors": [msg]}

    # Validate numerical and categorical features
    num_res = validate_numerical_features(df[NUMERICAL_FEATURES], raise_on_error=raise_on_error)
    cat_res = validate_categorical_features(df[CATEGORICAL_FEATURES], raise_on_error=raise_on_error)

    # Validate target if task specified and present
    target_res = {"valid": True, "errors": []}
    if task:
        target_col = get_target_for_task(task)
        if target_col in df.columns:
            s = df[target_col]
            errors = []
            if s.isna().any():
                errors.append(f"Target '{target_col}' contains null values.")
            if task.lower() in ("classification", "cls", CLASSIFICATION_TARGET.lower()):
                unique_vals = set(s.dropna().unique())
                if not unique_vals.issubset({0, 1}):
                    errors.append(f"Classification target '{target_col}' has invalid values: {unique_vals}")
            else:
                if (s < 0).any():
                    errors.append(f"Regression target '{target_col}' contains negative values.")
            if errors:
                target_res = {"valid": False, "errors": errors}
                if raise_on_error:
                    raise ValueError(f"Target validation failed: {errors}")

    all_valid = num_res["valid"] and cat_res["valid"] and target_res["valid"]
    all_errors = num_res.get("errors", []) + cat_res.get("errors", []) + target_res.get("errors", [])

    return {
        "valid": all_valid,
        "errors": all_errors,
    }


def build_preprocessor() -> ColumnTransformer:
    """
    Build scikit-learn ColumnTransformer for numerical passthrough and
    OneHotEncoder on categorical features.
    Configured with handle_unknown='ignore' for robust inference.
    """
    return ColumnTransformer(
        transformers=[
            ("num", "passthrough", NUMERICAL_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )


def fit_preprocessor(
    preprocessor_or_df: Any,
    X_train: Optional[pd.DataFrame] = None,
) -> ColumnTransformer:
    """
    Fit preprocessor on training features only to prevent data leakage.
    Supports both fit_preprocessor(preprocessor, X_train) and fit_preprocessor(X_train).
    """
    if isinstance(preprocessor_or_df, pd.DataFrame) and X_train is None:
        X_df = preprocessor_or_df
        preprocessor = build_preprocessor()
    elif isinstance(preprocessor_or_df, ColumnTransformer) and isinstance(X_train, pd.DataFrame):
        preprocessor = preprocessor_or_df
        X_df = X_train
    else:
        raise TypeError(
            f"Expected (ColumnTransformer, DataFrame) or (DataFrame), got ({type(preprocessor_or_df)}, {type(X_train)})"
        )

    check_feature_matrix_for_leakage(X_df)
    preprocessor.fit(X_df[APPROVED_FEATURES])
    logger.info("Preprocessor successfully fitted on %d training rows.", len(X_df))
    return preprocessor


def transform_features(
    preprocessor: ColumnTransformer,
    X: pd.DataFrame,
) -> np.ndarray:
    """
    Transform input features using fitted ColumnTransformer into a dense numpy array.
    """
    # Verify input has required features in correct order
    X_subset = X[APPROVED_FEATURES].copy()
    check_feature_matrix_for_leakage(X_subset)
    try:
        return preprocessor.transform(X_subset)
    except (AttributeError, TypeError):
        # Compatibility with ColumnTransformer unpickled across scikit-learn versions
        num_vals = X_subset[NUMERICAL_FEATURES].to_numpy(dtype=float)
        cat_encoder = getattr(preprocessor, "named_transformers_", {}).get("cat")
        if cat_encoder is not None:
            cat_vals = cat_encoder.transform(X_subset[CATEGORICAL_FEATURES])
            return np.hstack([num_vals, cat_vals])
        raise


def get_transformed_feature_names(preprocessor: ColumnTransformer) -> List[str]:
    """
    Get output feature names after one-hot encoding transformation.
    """
    try:
        if hasattr(preprocessor, "get_feature_names_out"):
            return list(preprocessor.get_feature_names_out())
    except (AttributeError, TypeError):
        pass
    # Fallback derivation
    names = [f"num__{col}" for col in NUMERICAL_FEATURES]
    cat_encoder = getattr(preprocessor, "named_transformers_", {}).get("cat")
    if cat_encoder and hasattr(cat_encoder, "categories_"):
        for feat_name, cats in zip(CATEGORICAL_FEATURES, cat_encoder.categories_):
            for cat in cats:
                names.append(f"cat__{feat_name}_{cat}")
    return names


def save_preprocessor(preprocessor: ColumnTransformer, filepath: Path) -> Path:
    """Save fitted preprocessor artifact to disk."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(preprocessor, filepath)
    logger.info("Saved preprocessor to: %s", filepath)
    return filepath


def load_preprocessor(filepath: Path) -> ColumnTransformer:
    """Load fitted preprocessor artifact from disk."""
    if not filepath.exists():
        raise FileNotFoundError(f"Preprocessor artifact not found at: {filepath}")
    preprocessor = joblib.load(filepath)
    return preprocessor
