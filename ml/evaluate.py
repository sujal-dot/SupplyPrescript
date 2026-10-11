"""
SupplyPrescript — Model Evaluation and Metrics Reporting
========================================================
Comprehensive evaluation metrics and visualization generation for:
1. Binary shipment delay classification (ROC-AUC, PR-AUC, Confusion Matrix, Brier score, threshold tuning).
2. Continuous delay duration regression (MAE, RMSE, R2, Median Absolute Error, Actual vs Predicted, Residuals).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # Headless rendering
import matplotlib.pyplot as plt
import numpy as np
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

logger = logging.getLogger("ml.evaluate")


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
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Compute comprehensive classification performance metrics.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)
    y_pred = (y_prob >= threshold).astype(int)

    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    brier = float(brier_score_loss(y_true, y_prob))

    # ROC-AUC & PR-AUC
    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None
    if len(np.unique(y_true)) > 1:
        roc_auc = float(roc_auc_score(y_true, y_prob))
        precisions, recalls, _ = precision_recall_curve(y_true, y_prob)
        pr_auc = float(auc(recalls, precisions))

    # Confusion matrix: [[TN, FP], [FN, TP]]
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = (int(x) for x in cm.ravel()) if cm.shape == (2, 2) else (0, 0, 0, 0)

    clf_report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)

    metrics = {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "pr_auc": round(pr_auc, 4) if pr_auc is not None else None,
        "brier_score": round(brier, 4),
        "threshold": round(threshold, 3),
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
    threshold: float = 0.5,
) -> List[Path]:
    """
    Generate and save classification visualization figures:
    - Confusion Matrix heatmap
    - ROC Curve
    - Precision-Recall Curve
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_plots: List[Path] = []
    y_pred = (y_prob >= threshold).astype(int)

    # 1. Confusion Matrix
    plt.figure(figsize=(6, 5))
    cm = confusion_matrix(y_true, y_pred)
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["On Time (0)", "Delayed (1)"],
        yticklabels=["On Time (0)", "Delayed (1)"],
    )
    plt.title(f"Confusion Matrix (Threshold = {threshold:.2f})")
    plt.ylabel("Actual")
    plt.xlabel("Predicted")
    plt.tight_layout()
    cm_path = output_dir / "confusion_matrix.png"
    plt.savefig(cm_path, dpi=150)
    plt.close()
    generated_plots.append(cm_path)

    # 2. ROC Curve
    if len(np.unique(y_true)) > 1:
        fpr, tpr, _ = roc_curve(y_true, y_prob)
        roc_val = roc_auc_score(y_true, y_prob)
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

        # 3. Precision-Recall Curve
        precisions, recalls, _ = precision_recall_curve(y_true, y_prob)
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
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> Dict[str, Any]:
    """
    Compute comprehensive regression performance metrics.
    Ensures predictions are non-negative.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    # Clip negative predictions to zero
    y_pred = np.clip(y_pred, 0.0, None)

    mae = float(mean_absolute_error(y_true, y_pred))
    mse = float(mean_squared_error(y_true, y_pred))
    rmse = float(np.sqrt(mse))
    r2 = float(r2_score(y_true, y_pred))
    med_ae = float(median_absolute_error(y_true, y_pred))
    max_err = float(np.max(np.abs(y_true - y_pred)))

    metrics = {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2_score": round(r2, 4),
        "median_absolute_error": round(med_ae, 4),
        "max_error": round(max_err, 4),
        "mean_actual_delay": round(float(np.mean(y_true)), 4),
        "mean_predicted_delay": round(float(np.mean(y_pred)), 4),
    }
    return metrics


def plot_regression_reports(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    output_dir: Path,
) -> List[Path]:
    """
    Generate and save regression visualization figures:
    - Actual vs Predicted plot
    - Residuals vs Predicted plot
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_plots: List[Path] = []
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.clip(np.asarray(y_pred, dtype=float), 0.0, None)
    residuals = y_true - y_pred

    # 1. Actual vs Predicted
    plt.figure(figsize=(6, 5))
    plt.scatter(y_true, y_pred, alpha=0.3, color="#2563eb", edgecolors="none", s=25)
    max_val = max(float(np.max(y_true)), float(np.max(y_pred)), 10.0)
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
    plt.scatter(y_pred, residuals, alpha=0.3, color="#7c3aed", edgecolors="none", s=25)
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
