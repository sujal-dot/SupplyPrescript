"""
SupplyPrescript — Model Evaluation and Quality Reporting
=========================================================
Comprehensive, reusable evaluation module for:
1. Binary shipment delay classification (ROC-AUC, PR-AUC, Confusion Matrix, Brier score, threshold metrics).
2. Continuous delay duration regression (MAE, RMSE, R2, MedAE, Actual vs Predicted, Residuals).

Supports CLI execution via: `python -m ml.evaluate`
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib
matplotlib.use("Agg")  # Headless rendering for automated server environments
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    auc,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    median_absolute_error,
    mean_squared_error,
    precision_recall_curve,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from ml.feature_config import (
    APPROVED_FEATURES,
    CLASSIFICATION_ARTIFACTS_DIR,
    CLASSIFICATION_DIR,
    CLASSIFICATION_REPORTS_DIR,
    CLASSIFICATION_TARGET,
    REGRESSION_ARTIFACTS_DIR,
    REGRESSION_DIR,
    REGRESSION_REPORTS_DIR,
    REGRESSION_TARGET,
)
from ml.leakage_checks import check_feature_matrix_for_leakage
from ml.preprocess import transform_features

logger = logging.getLogger("ml.evaluate")

DEFAULT_CLASSIFICATION_THRESHOLD = 0.150  # Tuned on validation split during Day 7


# ---------------------------------------------------------------------------
# Classification Evaluation
# ---------------------------------------------------------------------------
def find_optimal_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    metric: str = "f1",
) -> Tuple[float, Dict[str, Any]]:
    """
    Search candidate probability thresholds in [0.1, 0.9] to optimize a target validation metric (default F1).
    Returns: (best_threshold, threshold_grid_results)
    """
    thresholds = np.linspace(0.1, 0.9, 81)
    best_thresh = 0.5
    best_score = -1.0
    history: List[Dict[str, float]] = []

    for thresh in thresholds:
        y_pred = (y_prob >= thresh).astype(int)
        prec = float(precision_score(y_true, y_pred, zero_division=0))
        rec = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))
        acc = float(accuracy_score(y_true, y_pred))

        history.append({
            "threshold": round(float(thresh), 3),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "accuracy": round(acc, 4),
        })

        score_candidate = f1 if metric == "f1" else (prec + rec) / 2
        if score_candidate > best_score:
            best_score = score_candidate
            best_thresh = float(thresh)

    return round(best_thresh, 3), {"metric": metric, "best_threshold": round(best_thresh, 3), "history": history}


def evaluate_classification(
    y_true: Union[np.ndarray, List, pd.Series],
    y_prob: Union[np.ndarray, List, pd.Series],
    threshold: float = DEFAULT_CLASSIFICATION_THRESHOLD,
) -> Dict[str, Any]:
    """
    Compute comprehensive classification performance metrics.
    Robustly handles single-class test distributions, empty data, and class imbalance.
    """
    y_true_arr = np.asarray(y_true)
    y_prob_arr = np.asarray(y_prob, dtype=float)

    if len(y_true_arr) == 0 or len(y_prob_arr) == 0:
        raise ValueError("Cannot evaluate classification: dataset or predictions are empty.")

    if len(y_true_arr) != len(y_prob_arr):
        raise ValueError(
            f"Shape mismatch: y_true has {len(y_true_arr)} samples but y_prob has {len(y_prob_arr)} samples."
        )

    # Validate target values are boolean / 0 / 1
    unique_vals = np.unique(y_true_arr)
    for val in unique_vals:
        if val not in (0, 1, False, True, 0.0, 1.0):
            raise ValueError(f"Invalid classification target value: {val}. Expected binary {{0, 1}}.")

    y_true_clean = y_true_arr.astype(int)
    y_pred = (y_prob_arr >= threshold).astype(int)

    sample_count = len(y_true_clean)
    pos_count = int(np.sum(y_true_clean == 1))
    neg_count = int(np.sum(y_true_clean == 0))

    acc = float(accuracy_score(y_true_clean, y_pred))
    prec = float(precision_score(y_true_clean, y_pred, zero_division=0))
    rec = float(recall_score(y_true_clean, y_pred, zero_division=0))
    f1 = float(f1_score(y_true_clean, y_pred, zero_division=0))
    brier = float(brier_score_loss(y_true_clean, y_prob_arr))

    # ROC-AUC & PR-AUC with single-class safety
    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None
    roc_auc_reason: Optional[str] = None

    if len(unique_vals) > 1:
        roc_auc = float(roc_auc_score(y_true_clean, y_prob_arr))
        precisions, recalls, _ = precision_recall_curve(y_true_clean, y_prob_arr)
        pr_auc = float(auc(recalls, precisions))
    else:
        roc_auc_reason = (
            f"ROC-AUC is unavailable because only one class ({unique_vals[0]}) is present in the evaluated data."
        )
        logger.warning(roc_auc_reason)

    # Confusion matrix
    cm = confusion_matrix(y_true_clean, y_pred)
    if cm.shape == (2, 2):
        tn, fp, fn, tp = (int(x) for x in cm.ravel())
    elif cm.shape == (1, 1):
        if unique_vals[0] == 0:
            tn, fp, fn, tp = int(cm[0, 0]), 0, 0, 0
        else:
            tn, fp, fn, tp = 0, 0, 0, int(cm[0, 0])
    else:
        tn, fp, fn, tp = 0, 0, 0, 0

    clf_report = classification_report(y_true_clean, y_pred, output_dict=True, zero_division=0)

    metrics = {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "roc_auc_reason": roc_auc_reason,
        "pr_auc": round(pr_auc, 4) if pr_auc is not None else None,
        "brier_score": round(brier, 4),
        "threshold": round(threshold, 3),
        "sample_count": sample_count,
        "class_distribution": {
            "on_time_count": neg_count,
            "delayed_count": pos_count,
            "delayed_ratio": round(pos_count / sample_count, 4) if sample_count > 0 else 0.0,
        },
        "confusion_matrix": {
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "true_positives": tp,
            "matrix": cm.tolist(),
        },
        "classification_report": clf_report,
    }
    return metrics


def plot_classification_reports(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    output_dir: Path,
    threshold: float = DEFAULT_CLASSIFICATION_THRESHOLD,
) -> List[Path]:
    """
    Generate and save classification visualization figures:
    - Confusion Matrix heatmap
    - ROC Curve
    - Precision-Recall Curve
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_plots: List[Path] = []
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=float)
    y_pred = (y_prob_arr >= threshold).astype(int)

    # 1. Confusion Matrix
    plt.figure(figsize=(6, 5))
    cm = confusion_matrix(y_true_arr, y_pred)
    labels = ["On Time (0)", "Delayed (1)"] if cm.shape == (2, 2) else None
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=labels or True,
        yticklabels=labels or True,
    )
    plt.title(f"Confusion Matrix (Threshold = {threshold:.2f})")
    plt.ylabel("Actual")
    plt.xlabel("Predicted")
    plt.tight_layout()
    cm_path = output_dir / "confusion_matrix.png"
    plt.savefig(cm_path, dpi=150)
    plt.close()
    generated_plots.append(cm_path)

    # 2. ROC & PR Curves (only if at least 2 distinct classes present)
    if len(np.unique(y_true_arr)) > 1:
        fpr, tpr, _ = roc_curve(y_true_arr, y_prob_arr)
        roc_val = roc_auc_score(y_true_arr, y_prob_arr)
        plt.figure(figsize=(6, 5))
        plt.plot(fpr, tpr, color="#2563eb", lw=2, label=f"ROC curve (AUC = {roc_val:.3f})")
        plt.plot([0, 1], [0, 1], color="#9ca3af", lw=1.5, linestyle="--", label="Random Classifier")
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title("Receiver Operating Characteristic (ROC)")
        plt.legend(loc="lower right")
        plt.grid(True, linestyle=":", alpha=0.6)
        plt.tight_layout()
        roc_path = output_dir / "roc_curve.png"
        plt.savefig(roc_path, dpi=150)
        plt.close()
        generated_plots.append(roc_path)

        precisions, recalls, _ = precision_recall_curve(y_true_arr, y_prob_arr)
        pr_val = auc(recalls, precisions)
        plt.figure(figsize=(6, 5))
        plt.plot(recalls, precisions, color="#059669", lw=2, label=f"PR curve (AUC = {pr_val:.3f})")
        plt.xlabel("Recall")
        plt.ylabel("Precision")
        plt.title("Precision-Recall Curve")
        plt.legend(loc="lower left")
        plt.grid(True, linestyle=":", alpha=0.6)
        plt.tight_layout()
        pr_path = output_dir / "precision_recall_curve.png"
        plt.savefig(pr_path, dpi=150)
        plt.close()
        generated_plots.append(pr_path)

    logger.info("Saved %d classification plots to: %s", len(generated_plots), output_dir)
    return generated_plots


# ---------------------------------------------------------------------------
# Regression Evaluation
# ---------------------------------------------------------------------------
def evaluate_regression(
    y_true: Union[np.ndarray, List, pd.Series],
    y_pred: Union[np.ndarray, List, pd.Series],
) -> Dict[str, Any]:
    """
    Compute comprehensive regression performance metrics.
    Ensures non-negative prediction clipping and safely handles constant-target edge cases.
    """
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)

    if len(y_true_arr) == 0 or len(y_pred_arr) == 0:
        raise ValueError("Cannot evaluate regression: dataset or predictions are empty.")

    if len(y_true_arr) != len(y_pred_arr):
        raise ValueError(
            f"Shape mismatch: y_true has {len(y_true_arr)} samples but y_pred has {len(y_pred_arr)} samples."
        )

    # Check for NaN / infinite values
    if np.isnan(y_true_arr).any() or np.isinf(y_true_arr).any():
        raise ValueError("y_true contains NaN or infinite values.")

    # Production constraint: non-negative delay predictions
    y_pred_clean = np.clip(y_pred_arr, 0.0, None)

    sample_count = len(y_true_clean := y_true_arr)

    mae = float(mean_absolute_error(y_true_clean, y_pred_clean))
    mse = float(mean_squared_error(y_true_clean, y_pred_clean))
    rmse = float(np.sqrt(mse))
    med_ae = float(median_absolute_error(y_true_clean, y_pred_clean))
    max_err = float(np.max(np.abs(y_true_clean - y_pred_clean)))

    # Safe R2 calculation
    r2: Optional[float] = None
    r2_reason: Optional[str] = None
    if sample_count > 1 and np.var(y_true_clean) > 1e-12:
        r2 = float(r2_score(y_true_clean, y_pred_clean))
    else:
        r2_reason = "R-squared is undefined for a constant target distribution or single sample."
        logger.warning(r2_reason)

    metrics = {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2_score": round(r2, 4) if r2 is not None else None,
        "r2_reason": r2_reason,
        "median_absolute_error": round(med_ae, 4),
        "max_error": round(max_err, 4),
        "sample_count": sample_count,
        "target_distribution": {
            "mean": round(float(np.mean(y_true_clean)), 4),
            "std": round(float(np.std(y_true_clean)), 4),
            "min": round(float(np.min(y_true_clean)), 4),
            "max": round(float(np.max(y_true_clean)), 4),
        },
        "prediction_distribution": {
            "mean": round(float(np.mean(y_pred_clean)), 4),
            "std": round(float(np.std(y_pred_clean)), 4),
            "min": round(float(np.min(y_pred_clean)), 4),
            "max": round(float(np.max(y_pred_clean)), 4),
        },
    }
    return metrics


def plot_regression_reports(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    output_dir: Path,
) -> List[Path]:
    """
    Generate and save regression visualization figures:
    - Actual vs Predicted scatter plot
    - Residuals vs Predicted scatter plot
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_plots: List[Path] = []
    y_true_clean = np.asarray(y_true, dtype=float)
    y_pred_clean = np.clip(np.asarray(y_pred, dtype=float), 0.0, None)
    residuals = y_true_clean - y_pred_clean

    # 1. Actual vs Predicted
    plt.figure(figsize=(6, 5))
    plt.scatter(y_true_clean, y_pred_clean, alpha=0.3, color="#2563eb", edgecolors="none", s=25)
    max_val = max(float(np.max(y_true_clean)), float(np.max(y_pred_clean)), 10.0)
    plt.plot([0, max_val], [0, max_val], color="#dc2626", linestyle="--", lw=1.5, label="Perfect Fit (y = x)")
    plt.xlabel("Actual Delay (Days)")
    plt.ylabel("Predicted Delay (Days)")
    plt.title("Actual vs. Predicted Delay Days")
    plt.legend(loc="upper left")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    act_pred_path = output_dir / "actual_vs_predicted.png"
    plt.savefig(act_pred_path, dpi=150)
    plt.close()
    generated_plots.append(act_pred_path)

    # 2. Residuals vs Predicted
    plt.figure(figsize=(6, 5))
    plt.scatter(y_pred_clean, residuals, alpha=0.3, color="#7c3aed", edgecolors="none", s=25)
    plt.axhline(0, color="#dc2626", linestyle="--", lw=1.5)
    plt.xlabel("Predicted Delay (Days)")
    plt.ylabel("Residual (Actual - Predicted)")
    plt.title("Residuals vs. Predicted Delay")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    res_path = output_dir / "residuals.png"
    plt.savefig(res_path, dpi=150)
    plt.close()
    generated_plots.append(res_path)

    logger.info("Saved %d regression plots to: %s", len(generated_plots), output_dir)
    return generated_plots


def save_metrics_report(metrics: Dict[str, Any], filepath: Path) -> Path:
    """Save metrics dictionary as nicely formatted JSON."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Saved metrics to: %s", filepath)
    return filepath


# ---------------------------------------------------------------------------
# End-to-End Evaluation Pipeline
# ---------------------------------------------------------------------------
def run_classification_evaluation(
    model: Any = None,
    preprocessor: Any = None,
    test_df: Optional[pd.DataFrame] = None,
    threshold: Optional[float] = None,
    output_dir: Optional[Path] = CLASSIFICATION_REPORTS_DIR,
) -> Dict[str, Any]:
    """
    Run end-to-end evaluation on the classification model using the untouched test split.
    """
    from ml.model_registry import load_registered_model

    if model is None or preprocessor is None:
        model, preprocessor, meta = load_registered_model("classification")
        if threshold is None:
            threshold = float(meta.get("target", {}).get("classification_threshold", DEFAULT_CLASSIFICATION_THRESHOLD))

    eval_threshold = threshold if threshold is not None else DEFAULT_CLASSIFICATION_THRESHOLD

    if test_df is None:
        test_path = CLASSIFICATION_DIR / "test.csv"
        if not test_path.exists():
            raise FileNotFoundError(f"Test dataset not found at: {test_path}")
        test_df = pd.read_csv(test_path)

    if CLASSIFICATION_TARGET not in test_df.columns:
        raise ValueError(f"Target column '{CLASSIFICATION_TARGET}' missing in test dataset.")

    y_test = test_df[CLASSIFICATION_TARGET].values
    X_test_df = test_df[APPROVED_FEATURES].copy()
    check_feature_matrix_for_leakage(X_test_df)

    X_test_trans = transform_features(preprocessor, X_test_df)
    y_prob = model.predict_proba(X_test_trans)[:, 1]

    metrics = evaluate_classification(y_test, y_prob, threshold=eval_threshold)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        save_metrics_report(metrics, output_dir / "metrics.json")
        save_metrics_report(metrics["classification_report"], output_dir / "classification_report.json")
        plot_classification_reports(y_test, y_prob, output_dir, threshold=eval_threshold)

    return metrics


def run_regression_evaluation(
    model: Any = None,
    preprocessor: Any = None,
    test_df: Optional[pd.DataFrame] = None,
    output_dir: Optional[Path] = REGRESSION_REPORTS_DIR,
) -> Dict[str, Any]:
    """
    Run end-to-end evaluation on the regression model using the untouched test split.
    """
    from ml.model_registry import load_registered_model

    if model is None or preprocessor is None:
        model, preprocessor, meta = load_registered_model("regression")

    if test_df is None:
        test_path = REGRESSION_DIR / "test.csv"
        if not test_path.exists():
            raise FileNotFoundError(f"Test dataset not found at: {test_path}")
        test_df = pd.read_csv(test_path)

    if REGRESSION_TARGET not in test_df.columns:
        raise ValueError(f"Target column '{REGRESSION_TARGET}' missing in test dataset.")

    y_test = test_df[REGRESSION_TARGET].values
    X_test_df = test_df[APPROVED_FEATURES].copy()
    check_feature_matrix_for_leakage(X_test_df)

    X_test_trans = transform_features(preprocessor, X_test_df)
    y_pred = model.predict(X_test_trans)

    metrics = evaluate_regression(y_test, y_pred)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        save_metrics_report(metrics, output_dir / "metrics.json")
        plot_regression_reports(y_test, y_pred, output_dir)

    return metrics


def run_full_evaluation(
    register_version: Optional[str] = None,
    output_base_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run complete evaluation across both classification and regression test splits,
    saving metrics and visual reports. Optionally registers model version in models/versions/.
    """
    cls_out = (output_base_dir / "classification") if output_base_dir else CLASSIFICATION_REPORTS_DIR
    reg_out = (output_base_dir / "regression") if output_base_dir else REGRESSION_REPORTS_DIR

    logger.info("Evaluating Classification Model on test set...")
    cls_metrics = run_classification_evaluation(output_dir=cls_out)

    logger.info("Evaluating Regression Model on test set...")
    reg_metrics = run_regression_evaluation(output_dir=reg_out)

    combined_results = {
        "classification": cls_metrics,
        "regression": reg_metrics,
    }

    if register_version:
        from ml.model_registry import load_registered_model, register_model_version

        cls_model, preprocessor, meta = load_registered_model("classification")
        reg_model, _, _ = load_registered_model("regression")

        register_model_version(
            version=register_version,
            classifier=cls_model,
            regressor=reg_model,
            preprocessor=preprocessor,
            metadata=meta,
            metrics=combined_results,
            overwrite=True,
            set_active=True,
        )

    return combined_results


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def main() -> None:
    """CLI runner for evaluation pipeline."""
    parser = argparse.ArgumentParser(description="SupplyPrescript Model Evaluation Runner")
    parser.add_argument(
        "--task",
        choices=["all", "classification", "regression"],
        default="all",
        help="Task to evaluate (default: all)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_CLASSIFICATION_THRESHOLD,
        help=f"Classification decision threshold (default: {DEFAULT_CLASSIFICATION_THRESHOLD})",
    )
    parser.add_argument(
        "--register-version",
        type=str,
        default=None,
        help="Optional model version string to register/promote upon evaluation (e.g. v1.0)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 65)
    print(" SupplyPrescript — Model Evaluation Suite")
    print("=" * 65)

    if args.task in ("all", "classification"):
        print("\n--- Running Classification Evaluation ---")
        cls_res = run_classification_evaluation(threshold=args.threshold)
        print(f"Accuracy:    {cls_res['accuracy']:.4f}")
        print(f"Precision:   {cls_res['precision']:.4f}")
        print(f"Recall:      {cls_res['recall']:.4f}")
        print(f"F1-Score:    {cls_res['f1_score']:.4f}")
        print(f"ROC-AUC:     {cls_res['roc_auc'] if cls_res['roc_auc'] is not None else 'N/A'}")
        print(f"PR-AUC:      {cls_res['pr_auc'] if cls_res['pr_auc'] is not None else 'N/A'}")
        print(f"Threshold:   {cls_res['threshold']:.3f}")
        print(f"Delayed Pct: {cls_res['class_distribution']['delayed_ratio'] * 100:.2f}%")
        print(f"Samples:     {cls_res['sample_count']}")

    if args.task in ("all", "regression"):
        print("\n--- Running Regression Evaluation ---")
        reg_res = run_regression_evaluation()
        print(f"MAE:         {reg_res['mae']:.4f} days")
        print(f"RMSE:        {reg_res['rmse']:.4f} days")
        print(f"R² Score:    {reg_res['r2_score'] if reg_res['r2_score'] is not None else 'N/A'}")
        print(f"Median AE:   {reg_res['median_absolute_error']:.4f} days")
        print(f"Max Error:   {reg_res['max_error']:.4f} days")
        print(f"Mean Actual: {reg_res['target_distribution']['mean']:.4f} days")
        print(f"Samples:     {reg_res['sample_count']}")

    if args.register_version:
        from ml.model_registry import load_registered_model, register_model_version

        print(f"\nRegistering and promoting model version '{args.register_version}'...")
        cls_model, preprocessor, meta = load_registered_model("classification")
        reg_model, _, _ = load_registered_model("regression")
        comb_metrics = {
            "classification": cls_res if args.task in ("all", "classification") else {},
            "regression": reg_res if args.task in ("all", "regression") else {},
        }
        register_model_version(
            version=args.register_version,
            classifier=cls_model,
            regressor=reg_model,
            preprocessor=preprocessor,
            metadata=meta,
            metrics=comb_metrics,
            overwrite=True,
            set_active=True,
        )
        print(f"Version '{args.register_version}' successfully registered and promoted to active.")

    print("\n" + "=" * 65)
    print(" Evaluation Complete. Reports saved to ml/reports/.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
