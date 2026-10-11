"""
SupplyPrescript — Model Training Pipeline (Day 7)
=================================================
Trains, evaluates, and registers two production-grade XGBoost models:
1. Binary shipment delay classification (delayed in {0, 1})
2. Continuous delay days regression (delay_days >= 0)

Usage:
    python -m ml.train --model all
    python -m ml.train --model classification
    python -m ml.train --model regression
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
from xgboost import XGBClassifier, XGBRegressor

from ml.evaluate import (
    evaluate_classification,
    evaluate_regression,
    find_optimal_threshold,
    plot_classification_reports,
    plot_regression_reports,
    save_metrics_report,
)
from ml.feature_config import (
    APPROVED_FEATURES,
    CLASSIFICATION_ARTIFACTS_DIR,
    CLASSIFICATION_REPORTS_DIR,
    CLASSIFICATION_TARGET,
    DEFAULT_INPUT_PATH,
    RANDOM_SEED,
    REGRESSION_ARTIFACTS_DIR,
    REGRESSION_REPORTS_DIR,
    REGRESSION_TARGET,
)
from ml.leakage_checks import check_feature_matrix_for_leakage
from ml.model_registry import save_registered_model
from ml.preprocess import (
    build_preprocessor,
    fit_preprocessor,
    load_feature_splits,
    separate_features_and_target,
    transform_features,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ml.train")


def train_classification_model(
    data_dir: Optional[Path] = None,
    reports_dir: Path = CLASSIFICATION_REPORTS_DIR,
    threshold_metric: str = "f1",
) -> Dict[str, Any]:
    """
    Train, validate, tune threshold, and evaluate XGBoost delay classifier.
    """
    logger.info("=" * 65)
    logger.info("Starting Shipment Delay Classification Model Training")
    logger.info("=" * 65)

    reports_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load Day 6 feature splits
    train_df, val_df, test_df = load_feature_splits(task="classification", custom_dir=data_dir)

    # 2. Separate features and target
    X_train_df, y_train = separate_features_and_target(train_df, task="classification")
    X_val_df, y_val = separate_features_and_target(val_df, task="classification")
    X_test_df, y_test = separate_features_and_target(test_df, task="classification")

    # 3. Leakage checks
    check_feature_matrix_for_leakage(X_train_df)
    check_feature_matrix_for_leakage(X_val_df)
    check_feature_matrix_for_leakage(X_test_df)

    # 4. Build and fit preprocessor on training data only
    preprocessor = build_preprocessor()
    fit_preprocessor(preprocessor, X_train_df)

    # 5. Transform feature matrices
    X_train = transform_features(preprocessor, X_train_df)
    X_val = transform_features(preprocessor, X_val_df)
    X_test = transform_features(preprocessor, X_test_df)

    # Calculate class balance ratio for scale_pos_weight
    n_neg = int((y_train == 0).sum())
    n_pos = int((y_train == 1).sum())
    scale_pos_weight = round(n_neg / max(1, n_pos), 2)
    logger.info("Class distribution in train: 0=%d, 1=%d (scale_pos_weight: %.2f)", n_neg, n_pos, scale_pos_weight)

    # 6. Initialize candidate XGBClassifier
    hyperparams = {
        "n_estimators": 400,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "random_state": RANDOM_SEED,
        "n_jobs": -1,
    }

    model = XGBClassifier(**hyperparams)

    # 7. Train on training set with early stopping evaluation on validation set
    logger.info("Fitting XGBClassifier...")
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    # 8. Evaluate on validation set & Select Optimal Threshold
    val_probs = model.predict_proba(X_val)[:, 1]
    best_threshold, threshold_tuning_info = find_optimal_threshold(
        y_true=y_val.to_numpy(),
        y_prob=val_probs,
        metric=threshold_metric,
    )
    logger.info("Selected optimal classification threshold from validation: %.3f (optimized for %s)", best_threshold, threshold_metric)

    val_metrics = evaluate_classification(
        y_true=y_val.to_numpy(),
        y_prob=val_probs,
        threshold=best_threshold,
    )
    logger.info(
        "Validation Metrics: Accuracy=%.4f, Precision=%.4f, Recall=%.4f, F1=%.4f, ROC-AUC=%.4f",
        val_metrics["accuracy"], val_metrics["precision"], val_metrics["recall"], val_metrics["f1_score"], val_metrics["roc_auc"] or 0.0,
    )

    # 9. Final untouched test set evaluation
    test_probs = model.predict_proba(X_test)[:, 1]
    test_metrics = evaluate_classification(
        y_true=y_test.to_numpy(),
        y_prob=test_probs,
        threshold=best_threshold,
    )
    logger.info(
        "Test Metrics: Accuracy=%.4f, Precision=%.4f, Recall=%.4f, F1=%.4f, ROC-AUC=%.4f",
        test_metrics["accuracy"], test_metrics["precision"], test_metrics["recall"], test_metrics["f1_score"], test_metrics["roc_auc"] or 0.0,
    )

    # 10. Generate and save evaluation plots & metrics
    plot_classification_reports(
        y_true=y_test.to_numpy(),
        y_prob=test_probs,
        output_dir=reports_dir,
        threshold=best_threshold,
    )
    combined_metrics = {
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
        "threshold_selection": threshold_tuning_info,
    }
    save_metrics_report(combined_metrics, reports_dir / "metrics.json")

    # 11. Register and save model artifacts
    art_dir = save_registered_model(
        model=model,
        preprocessor=preprocessor,
        task="classification",
        validation_metrics=val_metrics,
        test_metrics=test_metrics,
        train_row_count=len(train_df),
        val_row_count=len(val_df),
        test_row_count=len(test_df),
        dataset_path=DEFAULT_INPUT_PATH,
        threshold=best_threshold,
        hyperparameters=hyperparams,
    )

    logger.info("Classification model trained and registered successfully in: %s", art_dir)
    return {
        "status": "SUCCESS",
        "task": "classification",
        "threshold": best_threshold,
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
    }


def train_regression_model(
    data_dir: Optional[Path] = None,
    reports_dir: Path = REGRESSION_REPORTS_DIR,
) -> Dict[str, Any]:
    """
    Train, validate, and evaluate XGBoost delay duration regressor.
    """
    logger.info("=" * 65)
    logger.info("Starting Shipment Delay Regression Model Training")
    logger.info("=" * 65)

    reports_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load Day 6 feature splits
    train_df, val_df, test_df = load_feature_splits(task="regression", custom_dir=data_dir)

    # 2. Separate features and target
    X_train_df, y_train = separate_features_and_target(train_df, task="regression")
    X_val_df, y_val = separate_features_and_target(val_df, task="regression")
    X_test_df, y_test = separate_features_and_target(test_df, task="regression")

    # 3. Leakage checks
    check_feature_matrix_for_leakage(X_train_df)
    check_feature_matrix_for_leakage(X_val_df)
    check_feature_matrix_for_leakage(X_test_df)

    # 4. Build and fit preprocessor on training data only
    preprocessor = build_preprocessor()
    fit_preprocessor(preprocessor, X_train_df)

    # 5. Transform feature matrices
    X_train = transform_features(preprocessor, X_train_df)
    X_val = transform_features(preprocessor, X_val_df)
    X_test = transform_features(preprocessor, X_test_df)

    # 6. Initialize candidate XGBRegressor
    hyperparams = {
        "n_estimators": 400,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "objective": "reg:squarederror",
        "random_state": RANDOM_SEED,
        "n_jobs": -1,
    }

    model = XGBRegressor(**hyperparams)

    # 7. Train regressor
    logger.info("Fitting XGBRegressor...")
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    # 8. Evaluate on validation set
    val_preds = np.clip(model.predict(X_val), 0.0, None)
    val_metrics = evaluate_regression(
        y_true=y_val.to_numpy(),
        y_pred=val_preds,
    )
    logger.info(
        "Validation Metrics: MAE=%.4f days, RMSE=%.4f days, R2=%.4f, Median AE=%.4f days",
        val_metrics["mae"], val_metrics["rmse"], val_metrics["r2_score"], val_metrics["median_absolute_error"],
    )

    # 9. Evaluate on untouched test set
    test_preds = np.clip(model.predict(X_test), 0.0, None)
    test_metrics = evaluate_regression(
        y_true=y_test.to_numpy(),
        y_pred=test_preds,
    )
    logger.info(
        "Test Metrics: MAE=%.4f days, RMSE=%.4f days, R2=%.4f, Median AE=%.4f days",
        test_metrics["mae"], test_metrics["rmse"], test_metrics["r2_score"], test_metrics["median_absolute_error"],
    )

    # 10. Generate and save evaluation plots & metrics
    plot_regression_reports(
        y_true=y_test.to_numpy(),
        y_pred=test_preds,
        output_dir=reports_dir,
    )
    combined_metrics = {
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
    }
    save_metrics_report(combined_metrics, reports_dir / "metrics.json")

    # 11. Register and save model artifacts
    art_dir = save_registered_model(
        model=model,
        preprocessor=preprocessor,
        task="regression",
        validation_metrics=val_metrics,
        test_metrics=test_metrics,
        train_row_count=len(train_df),
        val_row_count=len(val_df),
        test_row_count=len(test_df),
        dataset_path=DEFAULT_INPUT_PATH,
        hyperparameters=hyperparams,
    )

    logger.info("Regression model trained and registered successfully in: %s", art_dir)
    return {
        "status": "SUCCESS",
        "task": "regression",
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SupplyPrescript Phase 3 Day 7 — XGBoost Training Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model",
        type=str,
        default="all",
        choices=["all", "classification", "regression"],
        help="Specify which model to train ('all', 'classification', 'regression')",
    )
    args = parser.parse_args()

    success = True
    try:
        if args.model in ("all", "classification"):
            res_cls = train_classification_model()
            if res_cls.get("status") != "SUCCESS":
                success = False

        if args.model in ("all", "regression"):
            res_reg = train_regression_model()
            if res_reg.get("status") != "SUCCESS":
                success = False

    except Exception as exc:
        logger.error("Training failed with unexpected exception: %s", exc, exc_info=True)
        sys.exit(1)

    if not success:
        logger.error("Training completed with errors.")
        sys.exit(1)

    logger.info("=" * 65)
    logger.info("All requested models trained, evaluated, and saved successfully!")
    logger.info("=" * 65)


if __name__ == "__main__":
    main()
