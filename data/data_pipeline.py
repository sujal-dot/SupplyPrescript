"""
SupplyPrescript — Day 3 Data Pipeline
======================================
Loads, validates, cleans, and feature-engineers the synthetic shipment dataset.

Usage:
    python data/data_pipeline.py
    python data/data_pipeline.py --input data/synthetic/shipments.csv
    python data/data_pipeline.py --output data/processed/shipments_processed.csv

Pipeline flow:
    Raw CSV → Validate Schema → Profile → Clean → Feature Engineer → Validate → Save → Reports
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
_PIPELINE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _PIPELINE_DIR.parent

DEFAULT_INPUT = _PIPELINE_DIR / "synthetic" / "shipments.csv"
DEFAULT_SUPPLIERS = _PIPELINE_DIR / "synthetic" / "suppliers.csv"
DEFAULT_PRODUCTS = _PIPELINE_DIR / "synthetic" / "products.csv"
DEFAULT_OUTPUT = _PIPELINE_DIR / "processed" / "shipments_processed.csv"
DEFAULT_VAL_REPORT = _PIPELINE_DIR / "processed" / "validation_report.json"
DEFAULT_CLEAN_REPORT = _PIPELINE_DIR / "processed" / "cleaning_report.json"
DEFAULT_README = _PIPELINE_DIR / "processed" / "README.md"

# ---------------------------------------------------------------------------
# Required schema
# ---------------------------------------------------------------------------
REQUIRED_COLUMNS = [
    "shipment_id",
    "supplier_id",
    "product_id",
    "origin",
    "destination",
    "order_date",
    "expected_delivery_date",
    "actual_delivery_date",
    "lead_time",
    "quantity",
    "unit_cost",
    "shipping_cost",
    "supplier_reliability",
    "inventory_level",
    "demand",
    "priority",
    "transport_mode",
    "delay_days",
]

DATE_COLUMNS = ["order_date", "expected_delivery_date", "actual_delivery_date"]

NUMERIC_COLUMNS = [
    "lead_time",
    "quantity",
    "unit_cost",
    "shipping_cost",
    "supplier_reliability",
    "inventory_level",
    "demand",
    "delay_days",
]

CATEGORICAL_COLUMNS = ["origin", "destination", "priority", "transport_mode"]

VALID_TRANSPORT_MODES = {"Road", "Rail", "Air", "Sea"}
VALID_PRIORITIES = {"Low", "Medium", "High", "Critical"}

# Canonical mappings for fuzzy categorical cleaning
TRANSPORT_MODE_MAP: dict[str, str] = {
    "road": "Road",
    "rail": "Rail",
    "air": "Air",
    "sea": "Sea",
    "truck": "Road",
    "ship": "Sea",
    "ocean": "Sea",
    "train": "Rail",
    "flight": "Air",
    "plane": "Air",
    "highway": "Road",
}

PRIORITY_MAP: dict[str, str] = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "critical": "Critical",
    "urgent": "Critical",
    "normal": "Medium",
    "standard": "Low",
    "regular": "Low",
    "med": "Medium",
    "hi": "High",
    "crit": "Critical",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("data_pipeline")


# ---------------------------------------------------------------------------
# Step 1 — Load raw data
# ---------------------------------------------------------------------------
def load_data(input_path: Path) -> pd.DataFrame:
    """Load raw CSV into a DataFrame without modifying the source file."""
    logger.info("Loading data from %s ...", input_path)
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    # Read with explicit dtypes for performance; parse dates separately
    try:
        df = pd.read_csv(
            input_path,
            encoding="utf-8",
            dtype={
                "shipment_id": str,
                "supplier_id": str,
                "product_id": str,
                "origin": str,
                "destination": str,
                "priority": str,
                "transport_mode": str,
                "delay_reason": str,
            },
            low_memory=False,
        )
    except UnicodeDecodeError:
        # Fallback to latin-1
        df = pd.read_csv(
            input_path,
            encoding="latin-1",
            dtype={
                "shipment_id": str,
                "supplier_id": str,
                "product_id": str,
                "origin": str,
                "destination": str,
                "priority": str,
                "transport_mode": str,
                "delay_reason": str,
            },
            low_memory=False,
        )

    logger.info("Rows loaded: %d", len(df))
    logger.info("Columns found: %s", list(df.columns))
    return df


# ---------------------------------------------------------------------------
# Step 2 — Schema validation
# ---------------------------------------------------------------------------
def validate_schema(df: pd.DataFrame) -> None:
    """Verify all required columns are present. Abort on failure."""
    logger.info("Schema validation ...")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        logger.error("Schema validation FAILED — missing columns: %s", missing)
        sys.exit(1)
    logger.info("Schema validation: PASS")


# ---------------------------------------------------------------------------
# Step 3 — Initial data profile
# ---------------------------------------------------------------------------
def profile_data(df: pd.DataFrame) -> dict[str, Any]:
    """Generate a data profile without modifying the DataFrame."""
    logger.info("Profiling data ...")

    missing_per_col: dict[str, int] = {
        col: int(df[col].isna().sum()) for col in df.columns
    }
    dup_rows = int(df.duplicated().sum())
    dup_ids = int(df["shipment_id"].duplicated().sum()) if "shipment_id" in df.columns else 0

    numeric_stats: dict[str, Any] = {}
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            numeric_col = pd.to_numeric(df[col], errors="coerce")
            numeric_stats[col] = {
                "min": float(numeric_col.min()) if not numeric_col.isna().all() else None,
                "max": float(numeric_col.max()) if not numeric_col.isna().all() else None,
                "mean": float(numeric_col.mean()) if not numeric_col.isna().all() else None,
            }

    cat_unique: dict[str, list[str]] = {}
    for col in CATEGORICAL_COLUMNS:
        if col in df.columns:
            cat_unique[col] = sorted(df[col].dropna().unique().tolist())

    profile = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "missing_values_per_column": missing_per_col,
        "total_missing": sum(missing_per_col.values()),
        "duplicate_rows": dup_rows,
        "duplicate_shipment_ids": dup_ids,
        "data_types": {col: str(df[col].dtype) for col in df.columns},
        "numeric_stats": numeric_stats,
        "categorical_unique_values": cat_unique,
    }

    logger.info("  Rows: %d | Columns: %d", profile["row_count"], profile["column_count"])
    logger.info("  Total missing values: %d", profile["total_missing"])
    logger.info("  Duplicate rows: %d", dup_rows)
    logger.info("  Duplicate shipment_ids: %d", dup_ids)
    return profile


# ---------------------------------------------------------------------------
# Step 4 — Numeric type coercion (non-destructive; records errors)
# ---------------------------------------------------------------------------
def coerce_numeric_columns(df: pd.DataFrame, stats: dict[str, Any]) -> pd.DataFrame:
    """
    Convert numeric columns to proper types.
    Invalid values become NaN (recorded in stats for imputation tracking).
    """
    logger.info("Coercing numeric column types ...")
    df = df.copy()
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            original_nulls = df[col].isna().sum()
            df[col] = pd.to_numeric(df[col], errors="coerce")
            new_nulls = df[col].isna().sum()
            coercion_errors = int(new_nulls - original_nulls)
            if coercion_errors > 0:
                logger.warning("  %s: %d values could not be converted → set to NaN", col, coercion_errors)
                stats.setdefault("coercion_errors", {})[col] = coercion_errors
    return df


# ---------------------------------------------------------------------------
# Step 5 — Missing value handling
# ---------------------------------------------------------------------------
def clean_missing_values(df: pd.DataFrame, stats: dict[str, Any]) -> pd.DataFrame:
    """Handle missing values with appropriate strategies per column type."""
    logger.info("Checking missing values ...")

    df = df.copy()
    removed_rows = 0
    imputed: dict[str, int] = {}
    filled_categorical: dict[str, int] = {}

    # --- Critical ID fields: remove if missing ---
    id_cols = ["shipment_id", "supplier_id", "product_id"]
    for col in id_cols:
        if col in df.columns:
            missing_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
            n_missing = missing_mask.sum()
            if n_missing > 0:
                logger.warning("  %s: %d missing critical ID → rows removed", col, n_missing)
                df = df[~missing_mask].copy()
                removed_rows += n_missing

    stats["missing_id_rows_removed"] = removed_rows

    # --- Categorical fields: fill with 'Unknown' ---
    for col in ["origin", "destination", "priority", "transport_mode"]:
        if col in df.columns:
            missing_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
            n_missing = int(missing_mask.sum())
            if n_missing > 0:
                df.loc[missing_mask, col] = "Unknown"
                filled_categorical[col] = n_missing
                logger.info("  %s: %d missing → filled 'Unknown'", col, n_missing)

    stats["missing_categorical_filled"] = filled_categorical

    # --- Numerical fields: group-aware median imputation ---
    numeric_impute_cols = [
        "quantity", "unit_cost", "shipping_cost",
        "inventory_level", "demand", "supplier_reliability",
    ]
    for col in numeric_impute_cols:
        if col in df.columns:
            missing_mask = df[col].isna()
            n_missing = int(missing_mask.sum())
            if n_missing > 0:
                # Prefer group-level median (by supplier_id)
                if "supplier_id" in df.columns and col not in ["supplier_reliability"]:
                    group_median = df.groupby("supplier_id")[col].transform("median")
                    df.loc[missing_mask, col] = group_median[missing_mask]
                    # For any still missing (entire group is NaN), fall back to global median
                    still_missing = df[col].isna()
                    if still_missing.any():
                        global_median = df[col].median()
                        df.loc[still_missing, col] = global_median
                else:
                    global_median = df[col].median()
                    df.loc[missing_mask, col] = global_median
                imputed[col] = n_missing
                logger.info("  %s: %d missing → imputed via median", col, n_missing)

    stats["missing_numeric_imputed"] = imputed

    # --- lead_time and delay_days: imputed or derived later ---
    for col in ["lead_time", "delay_days"]:
        if col in df.columns:
            missing_mask = df[col].isna()
            n_missing = int(missing_mask.sum())
            if n_missing > 0:
                global_median = df[col].median()
                df.loc[missing_mask, col] = global_median
                imputed[col] = n_missing
                logger.info("  %s: %d missing → imputed (will be recalculated from dates)", col, n_missing)

    logger.info("Checking missing values ... done")
    return df


# ---------------------------------------------------------------------------
# Step 6 — Duplicate removal
# ---------------------------------------------------------------------------
def remove_duplicates(df: pd.DataFrame, stats: dict[str, Any]) -> pd.DataFrame:
    """Remove duplicate rows and duplicate shipment IDs."""
    logger.info("Checking duplicates ...")

    df = df.copy()
    n_before = len(df)

    # Remove fully duplicate rows first (keep the first)
    dup_rows_mask = df.duplicated(keep="first")
    n_dup_rows = int(dup_rows_mask.sum())
    df = df[~dup_rows_mask].copy()
    logger.info("  Duplicate rows found and removed: %d", n_dup_rows)

    # Remove duplicate shipment IDs — keep the most complete record
    dup_id_mask = df.duplicated(subset=["shipment_id"], keep=False)
    dup_ids = df.loc[dup_id_mask, "shipment_id"].unique()
    n_dup_ids = len(dup_ids)

    if n_dup_ids > 0:
        logger.warning("  Duplicate shipment_ids found: %d", n_dup_ids)
        # Score completeness as count of non-null values per row
        completeness = df.notna().sum(axis=1)
        # For each duplicate group, keep the row with most non-null values
        df["_completeness"] = completeness
        df = (
            df.sort_values("_completeness", ascending=False)
            .drop_duplicates(subset=["shipment_id"], keep="first")
            .drop(columns=["_completeness"])
        )

    n_after = len(df)
    rows_removed = n_before - n_after

    stats["duplicate_rows_found"] = n_dup_rows
    stats["duplicate_rows_removed"] = n_dup_rows
    stats["duplicate_shipment_ids"] = n_dup_ids
    stats["duplicate_id_rows_removed"] = max(0, rows_removed - n_dup_rows)

    logger.info("  Rows after deduplication: %d (removed %d total)", n_after, rows_removed)
    return df


# ---------------------------------------------------------------------------
# Step 7 — Date parsing and validation
# ---------------------------------------------------------------------------
def clean_dates(df: pd.DataFrame, stats: dict[str, Any]) -> pd.DataFrame:
    """
    Parse date columns and enforce logical ordering:
        order_date <= expected_delivery_date
        order_date <= actual_delivery_date
    """
    logger.info("Checking dates ...")

    df = df.copy()
    invalid_dates = 0
    invalid_dates_fixed = 0
    rows_removed_dates = 0

    for col in DATE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", format="%Y-%m-%d")
            n_failed = int(df[col].isna().sum())
            if n_failed > 0:
                logger.warning("  %s: %d unparseable dates → NaT", col, n_failed)
                invalid_dates += n_failed

    # Remove rows where order_date is missing (cannot be reconstructed)
    missing_order = df["order_date"].isna()
    if missing_order.any():
        n = int(missing_order.sum())
        logger.warning("  order_date missing %d rows → removed", n)
        df = df[~missing_order].copy()
        rows_removed_dates += n

    # Attempt to reconstruct expected_delivery_date from order_date + lead_time
    missing_exp = df["expected_delivery_date"].isna()
    if missing_exp.any():
        n = int(missing_exp.sum())
        if "lead_time" in df.columns:
            reconstructed = df.loc[missing_exp, "order_date"] + pd.to_timedelta(
                pd.to_numeric(df.loc[missing_exp, "lead_time"], errors="coerce").fillna(7).astype(int),
                unit="D",
            )
            df.loc[missing_exp, "expected_delivery_date"] = reconstructed
            invalid_dates_fixed += int(missing_exp.sum())
            logger.info("  expected_delivery_date: %d missing → reconstructed from order_date + lead_time", n)
        else:
            df = df[~missing_exp].copy()
            rows_removed_dates += n

    # Attempt to reconstruct actual_delivery_date from expected + delay_days
    missing_act = df["actual_delivery_date"].isna()
    if missing_act.any():
        n = int(missing_act.sum())
        if "delay_days" in df.columns:
            delay_series = pd.to_numeric(df.loc[missing_act, "delay_days"], errors="coerce").fillna(0).astype(int)
            reconstructed = df.loc[missing_act, "expected_delivery_date"] + pd.to_timedelta(delay_series, unit="D")
            df.loc[missing_act, "actual_delivery_date"] = reconstructed
            invalid_dates_fixed += n
            logger.info("  actual_delivery_date: %d missing → reconstructed from expected + delay_days", n)
        else:
            df = df[~missing_act].copy()
            rows_removed_dates += n

    # Logical date order enforcement: order_date <= expected_delivery_date
    bad_exp = df["expected_delivery_date"] < df["order_date"]
    if bad_exp.any():
        n = int(bad_exp.sum())
        logger.warning("  %d rows: expected_delivery_date < order_date → swapped", n)
        df.loc[bad_exp, ["order_date", "expected_delivery_date"]] = df.loc[
            bad_exp, ["expected_delivery_date", "order_date"]
        ].values
        invalid_dates_fixed += n

    # Logical date order enforcement: order_date <= actual_delivery_date
    bad_act = df["actual_delivery_date"] < df["order_date"]
    if bad_act.any():
        n = int(bad_act.sum())
        logger.warning("  %d rows: actual_delivery_date < order_date → set to order_date", n)
        df.loc[bad_act, "actual_delivery_date"] = df.loc[bad_act, "order_date"]
        invalid_dates_fixed += n

    stats["invalid_dates_found"] = invalid_dates
    stats["invalid_dates_fixed"] = invalid_dates_fixed
    stats["rows_removed_bad_dates"] = rows_removed_dates

    logger.info("Checking dates ... done")
    return df


# ---------------------------------------------------------------------------
# Step 8 — Lead-time recalculation and outlier detection
# ---------------------------------------------------------------------------
def handle_abnormal_lead_times(df: pd.DataFrame, stats: dict[str, Any]) -> pd.DataFrame:
    """
    Recalculate lead_time from actual dates, flag statistical outliers,
    but keep valid extreme values.
    """
    logger.info("Checking lead times ...")

    df = df.copy()

    # Recalculate from actual dates
    calculated = (df["actual_delivery_date"] - df["order_date"]).dt.days
    original = pd.to_numeric(df["lead_time"], errors="coerce")

    mismatches = (calculated != original) & calculated.notna() & original.notna()
    n_mismatch = int(mismatches.sum())
    if n_mismatch > 0:
        logger.info("  lead_time mismatch (dates vs. stored value): %d → corrected", n_mismatch)
        df.loc[mismatches, "lead_time"] = calculated[mismatches]

    # Fill any remaining NaN lead_times
    still_null = df["lead_time"].isna() | (calculated.isna() & df["lead_time"].isna())
    if "lead_time" in df.columns:
        null_mask = df["lead_time"].isna()
        if null_mask.any():
            df.loc[null_mask, "lead_time"] = calculated[null_mask].fillna(df["lead_time"].median())

    # Ensure lead_time > 0
    invalid_lt = df["lead_time"] <= 0
    if invalid_lt.any():
        n = int(invalid_lt.sum())
        logger.warning("  %d rows with lead_time <= 0 → recalculated from dates", n)
        df.loc[invalid_lt, "lead_time"] = calculated[invalid_lt].clip(lower=1)

    df["lead_time"] = df["lead_time"].astype(float)

    # IQR outlier detection (statistical, NOT automatic deletion)
    q1 = df["lead_time"].quantile(0.25)
    q3 = df["lead_time"].quantile(0.75)
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr

    outlier_mask = (df["lead_time"] < lower_fence) | (df["lead_time"] > upper_fence)
    df["lead_time_outlier"] = outlier_mask.astype(int)
    n_outliers = int(outlier_mask.sum())
    logger.info(
        "  Lead-time IQR fences: [%.1f, %.1f] | Outliers flagged: %d (kept in dataset)",
        lower_fence, upper_fence, n_outliers,
    )

    stats["abnormal_lead_times_found"] = n_outliers
    stats["lead_times_corrected"] = n_mismatch

    logger.info("Checking lead times ... done")
    return df


# ---------------------------------------------------------------------------
# Step 9 — Negative quantity handling
# ---------------------------------------------------------------------------
def clean_numeric_values(df: pd.DataFrame, stats: dict[str, Any]) -> pd.DataFrame:
    """Validate and clean all numeric business-rule constraints."""
    logger.info("Checking numerical values ...")

    df = df.copy()
    neg_qty_found = 0
    neg_qty_fixed = 0
    numeric_corrections = {}

    # --- quantity > 0 ---
    negative_qty = df["quantity"] < 0
    neg_qty_found = int(negative_qty.sum())
    if neg_qty_found > 0:
        logger.warning("  quantity < 0: %d rows found", neg_qty_found)
        # Strategy: negative likely a data-entry sign error → flag and correct
        df.loc[negative_qty, "quantity"] = df.loc[negative_qty, "quantity"].abs()
        neg_qty_fixed = neg_qty_found
        logger.info("  quantity: %d negatives corrected (sign flip — sign-error assumption)", neg_qty_fixed)

    zero_qty = df["quantity"] <= 0
    if zero_qty.any():
        n = int(zero_qty.sum())
        logger.warning("  quantity <= 0: %d rows → imputed with group median (positive values only)", n)
        # Compute group median only from strictly positive rows to avoid contamination
        positive_mask = df["quantity"] > 0
        group_med = df[positive_mask].groupby("product_id")["quantity"].median()
        for idx in df.index[zero_qty]:
            pid = df.at[idx, "product_id"]
            if pid in group_med.index and group_med[pid] > 0:
                df.at[idx, "quantity"] = group_med[pid]
            else:
                # Fallback to global positive median
                global_pos_med = df.loc[positive_mask, "quantity"].median()
                df.at[idx, "quantity"] = global_pos_med if global_pos_med > 0 else 1.0
        numeric_corrections["quantity_zero_imputed"] = n

    stats["negative_quantities_found"] = neg_qty_found
    stats["negative_quantities_fixed"] = neg_qty_fixed

    # --- unit_cost > 0 ---
    invalid_cost = df["unit_cost"] <= 0
    if invalid_cost.any():
        n = int(invalid_cost.sum())
        grp_med = df.groupby("product_id")["unit_cost"].transform("median")
        df.loc[invalid_cost, "unit_cost"] = grp_med[invalid_cost].fillna(df["unit_cost"].median())
        numeric_corrections["unit_cost_corrected"] = n
        logger.warning("  unit_cost <= 0: %d → group median imputed", n)

    # --- shipping_cost >= 0 ---
    neg_ship = df["shipping_cost"] < 0
    if neg_ship.any():
        n = int(neg_ship.sum())
        df.loc[neg_ship, "shipping_cost"] = df.loc[neg_ship, "shipping_cost"].abs()
        numeric_corrections["shipping_cost_negated"] = n
        logger.warning("  shipping_cost < 0: %d → abs()", n)

    # --- inventory_level >= 0 ---
    neg_inv = df["inventory_level"] < 0
    if neg_inv.any():
        n = int(neg_inv.sum())
        df.loc[neg_inv, "inventory_level"] = 0
        numeric_corrections["inventory_level_clipped"] = n
        logger.warning("  inventory_level < 0: %d → set to 0", n)

    # --- demand >= 0 ---
    neg_demand = df["demand"] < 0
    if neg_demand.any():
        n = int(neg_demand.sum())
        df.loc[neg_demand, "demand"] = df.loc[neg_demand, "demand"].abs()
        numeric_corrections["demand_negated"] = n
        logger.warning("  demand < 0: %d → abs()", n)

    # --- supplier_reliability between 0 and 1 ---
    # Handle percentage encoding (e.g., 70–99 instead of 0.70–0.99)
    pct_scale = (df["supplier_reliability"] > 1.0) & (df["supplier_reliability"] <= 100.0)
    if pct_scale.any():
        n = int(pct_scale.sum())
        df.loc[pct_scale, "supplier_reliability"] = df.loc[pct_scale, "supplier_reliability"] / 100.0
        numeric_corrections["supplier_reliability_rescaled"] = n
        logger.info("  supplier_reliability: %d percentage values rescaled to [0,1]", n)

    out_of_range = (df["supplier_reliability"] < 0) | (df["supplier_reliability"] > 1)
    if out_of_range.any():
        n = int(out_of_range.sum())
        df.loc[out_of_range, "supplier_reliability"] = df["supplier_reliability"].clip(0, 1)
        numeric_corrections["supplier_reliability_clipped"] = n
        logger.warning("  supplier_reliability out of [0,1]: %d → clipped", n)

    # --- delay_days >= 0 ---
    neg_delay = df["delay_days"] < 0
    if neg_delay.any():
        n = int(neg_delay.sum())
        df.loc[neg_delay, "delay_days"] = 0
        numeric_corrections["delay_days_clipped"] = n
        logger.warning("  delay_days < 0: %d → set to 0", n)

    stats["numeric_corrections"] = numeric_corrections
    logger.info("Checking numerical values ... done")
    return df


# ---------------------------------------------------------------------------
# Step 10 — Categorical value normalization
# ---------------------------------------------------------------------------
def clean_categorical_values(df: pd.DataFrame, stats: dict[str, Any]) -> pd.DataFrame:
    """Normalize categorical columns for consistent encoding."""
    logger.info("Checking categorical values ...")

    df = df.copy()
    invalid_categories_found = 0
    cat_corrections: dict[str, int] = {}

    def normalize_cat(val: str, canonical_map: dict[str, str], valid_set: set[str]) -> str:
        """Normalize a single categorical value."""
        if pd.isna(val):
            return "Unknown"
        stripped = str(val).strip()
        if not stripped:
            return "Unknown"
        # Already valid (case-sensitive check)
        if stripped in valid_set:
            return stripped
        # Try case-insensitive lookup in map
        key = stripped.lower()
        if key in canonical_map:
            return canonical_map[key]
        # Try direct title-case match against valid set
        title_case = stripped.title()
        if title_case in valid_set:
            return title_case
        # Unknown
        return "Unknown"

    # Transport mode
    before = df["transport_mode"].copy()
    df["transport_mode"] = df["transport_mode"].apply(
        lambda v: normalize_cat(v, TRANSPORT_MODE_MAP, VALID_TRANSPORT_MODES)
    )
    changed = (df["transport_mode"] != before).sum()
    if changed:
        cat_corrections["transport_mode"] = int(changed)
        logger.info("  transport_mode: %d values normalized", changed)

    # Unknown transport_mode
    unknown_tm = (df["transport_mode"] == "Unknown").sum()
    if unknown_tm:
        invalid_categories_found += int(unknown_tm)
        logger.warning("  transport_mode: %d unrecognized → 'Unknown'", unknown_tm)

    # Priority
    before = df["priority"].copy()
    df["priority"] = df["priority"].apply(
        lambda v: normalize_cat(v, PRIORITY_MAP, VALID_PRIORITIES)
    )
    changed = (df["priority"] != before).sum()
    if changed:
        cat_corrections["priority"] = int(changed)
        logger.info("  priority: %d values normalized", changed)

    unknown_pri = (df["priority"] == "Unknown").sum()
    if unknown_pri:
        invalid_categories_found += int(unknown_pri)
        logger.warning("  priority: %d unrecognized → 'Unknown'", unknown_pri)

    # Origin / Destination: strip and title-case
    for col in ["origin", "destination"]:
        before = df[col].copy()
        df[col] = df[col].str.strip().str.title()
        changed = (df[col] != before).sum()
        if changed:
            cat_corrections[col] = int(changed)

    stats["invalid_categories_found"] = invalid_categories_found
    stats["categorical_corrections"] = cat_corrections

    logger.info("Checking categorical values ... done")
    return df


# ---------------------------------------------------------------------------
# Step 11 — Delay recalculation
# ---------------------------------------------------------------------------
def recalculate_derived_fields(df: pd.DataFrame, stats: dict[str, Any]) -> pd.DataFrame:
    """
    Recalculate delay_days from dates.
    delay_days = max(0, actual_delivery_date - expected_delivery_date)
    """
    logger.info("Recalculating derived fields ...")

    df = df.copy()
    calculated_delay = (df["actual_delivery_date"] - df["expected_delivery_date"]).dt.days.clip(lower=0)
    original_delay = pd.to_numeric(df["delay_days"], errors="coerce")

    mismatch_mask = (calculated_delay != original_delay) & calculated_delay.notna()
    n_mismatch = int(mismatch_mask.sum())
    if n_mismatch > 0:
        logger.info("  delay_days mismatch: %d → corrected from dates", n_mismatch)

    df["delay_days"] = calculated_delay.fillna(original_delay).fillna(0).astype(int)

    stats["delay_days_corrected"] = n_mismatch
    logger.info("Recalculating derived fields ... done")
    return df


# ---------------------------------------------------------------------------
# Step 12 — Reference validation (supplier/product IDs)
# ---------------------------------------------------------------------------
def validate_references(
    df: pd.DataFrame,
    suppliers_path: Path,
    products_path: Path,
    stats: dict[str, Any],
) -> pd.DataFrame:
    """Validate supplier_id and product_id against reference tables."""
    logger.info("Validating references ...")

    df = df.copy()
    orphan_suppliers = 0
    orphan_products = 0

    if suppliers_path.exists():
        suppliers_df = pd.read_csv(suppliers_path, dtype={"supplier_id": str})
        valid_suppliers = set(suppliers_df["supplier_id"].dropna().unique())
        orphan_mask = ~df["supplier_id"].isin(valid_suppliers)
        orphan_suppliers = int(orphan_mask.sum())
        if orphan_suppliers > 0:
            logger.warning("  Orphan supplier_ids: %d rows → removed", orphan_suppliers)
            df = df[~orphan_mask].copy()
    else:
        logger.warning("  suppliers.csv not found at %s — skipping supplier validation", suppliers_path)

    if products_path.exists():
        products_df = pd.read_csv(products_path, dtype={"product_id": str})
        valid_products = set(products_df["product_id"].dropna().unique())
        orphan_mask = ~df["product_id"].isin(valid_products)
        orphan_products = int(orphan_mask.sum())
        if orphan_products > 0:
            logger.warning("  Orphan product_ids: %d rows → removed", orphan_products)
            df = df[~orphan_mask].copy()
    else:
        logger.warning("  products.csv not found at %s — skipping product validation", products_path)

    stats["orphan_suppliers"] = orphan_suppliers
    stats["orphan_products"] = orphan_products
    logger.info("  Orphan suppliers: %d | Orphan products: %d", orphan_suppliers, orphan_products)
    logger.info("Validating references ... done")
    return df


# ---------------------------------------------------------------------------
# Step 13 — Feature Engineering
# ---------------------------------------------------------------------------
def engineer_features(df: pd.DataFrame, stats: dict[str, Any]) -> pd.DataFrame:
    """Add engineered features for downstream ML and analytics."""
    logger.info("Feature engineering ...")

    df = df.copy()
    features_before = len(df.columns)

    # Delivery status
    df["is_delayed"] = (df["delay_days"] > 0).astype(int)
    df["delivery_status"] = df["is_delayed"].map({0: "On Time", 1: "Delayed"})

    # Inventory shortage flag
    df["inventory_shortage"] = (df["inventory_level"] < df["demand"]).astype(int)

    # Inventory coverage ratio (protected against division by zero)
    df["inventory_coverage_ratio"] = np.where(
        df["demand"] > 0,
        df["inventory_level"] / df["demand"],
        np.inf,
    ).round(4)

    # Cost features
    df["total_product_cost"] = (df["quantity"] * df["unit_cost"]).round(2)
    df["total_cost"] = (df["total_product_cost"] + df["shipping_cost"]).round(2)

    # Date-based features
    df["order_year"] = df["order_date"].dt.year
    df["order_month"] = df["order_date"].dt.month
    df["order_quarter"] = df["order_date"].dt.quarter
    df["order_day_of_week"] = df["order_date"].dt.dayofweek  # 0=Monday, 6=Sunday
    df["is_weekend_order"] = (df["order_day_of_week"] >= 5).astype(int)

    # Lead-time category based on cleaned dataset quantiles
    lt_q33 = df["lead_time"].quantile(0.33)
    lt_q66 = df["lead_time"].quantile(0.66)
    # Guard against duplicate bin edges (e.g. when all values are equal in tests)
    try:
        df["lead_time_category"] = pd.cut(
            df["lead_time"],
            bins=[-np.inf, lt_q33, lt_q66, np.inf],
            labels=["Short", "Medium", "Long"],
            right=True,
            duplicates="drop",
        ).astype(str)
    except ValueError:
        # Degenerate distribution: assign all rows to "Medium"
        df["lead_time_category"] = "Medium"

    features_after = len(df.columns)
    new_features = features_after - features_before
    stats["features_added"] = new_features
    logger.info("  Added %d engineered features", new_features)
    logger.info("Feature engineering ... done")
    return df


# ---------------------------------------------------------------------------
# Step 14 — Final validation
# ---------------------------------------------------------------------------
def validate_processed_data(df: pd.DataFrame) -> dict[str, bool]:
    """Run final assertions on the processed dataset."""
    logger.info("Running final validation ...")

    results: dict[str, bool] = {}

    results["no_duplicate_shipment_ids"] = not df["shipment_id"].duplicated().any()
    results["no_missing_shipment_id"] = df["shipment_id"].notna().all()
    results["no_missing_supplier_id"] = df["supplier_id"].notna().all()
    results["no_missing_product_id"] = df["product_id"].notna().all()

    results["no_invalid_dates"] = (
        df["order_date"].notna().all()
        and df["expected_delivery_date"].notna().all()
        and df["actual_delivery_date"].notna().all()
    )
    results["order_date_lte_expected"] = (df["order_date"] <= df["expected_delivery_date"]).all()
    results["order_date_lte_actual"] = (df["order_date"] <= df["actual_delivery_date"]).all()

    results["no_negative_quantity"] = (df["quantity"] > 0).all()
    results["no_invalid_cost"] = (df["unit_cost"] > 0).all() and (df["shipping_cost"] >= 0).all()
    results["supplier_reliability_valid"] = (
        (df["supplier_reliability"] >= 0) & (df["supplier_reliability"] <= 1)
    ).all()
    results["no_negative_inventory"] = (df["inventory_level"] >= 0).all()
    results["no_negative_demand"] = (df["demand"] >= 0).all()
    results["no_negative_delay"] = (df["delay_days"] >= 0).all()
    results["no_invalid_lead_time"] = (df["lead_time"] > 0).all()

    results["valid_transport_modes"] = df["transport_mode"].isin(
        VALID_TRANSPORT_MODES | {"Unknown"}
    ).all()
    results["valid_priorities"] = df["priority"].isin(
        VALID_PRIORITIES | {"Unknown"}
    ).all()

    # Formula checks
    expected_delay = (df["actual_delivery_date"] - df["expected_delivery_date"]).dt.days.clip(lower=0)
    results["delay_days_formula_correct"] = (df["delay_days"] == expected_delay).all()

    expected_lt = (df["actual_delivery_date"] - df["order_date"]).dt.days
    results["lead_time_formula_correct"] = (
        (df["lead_time"].astype(int) == expected_lt.astype(int)).all()
    )

    results["is_delayed_formula_correct"] = (df["is_delayed"] == (df["delay_days"] > 0).astype(int)).all()
    results["inventory_shortage_formula"] = (
        df["inventory_shortage"] == (df["inventory_level"] < df["demand"]).astype(int)
    ).all()
    results["total_product_cost_formula"] = (
        (df["total_product_cost"] - df["quantity"] * df["unit_cost"]).abs() < 0.01
    ).all()
    results["total_cost_formula"] = (
        (df["total_cost"] - (df["total_product_cost"] + df["shipping_cost"])).abs() < 0.01
    ).all()

    all_pass = all(results.values())
    for check, passed in results.items():
        if not passed:
            logger.error("  FAIL: %s", check)

    if all_pass:
        logger.info("Final validation: PASS ✓")
    else:
        failed = [k for k, v in results.items() if not v]
        logger.error("Final validation: FAIL — %d checks failed: %s", len(failed), failed)

    return results


# ---------------------------------------------------------------------------
# Step 15 — Save processed data
# ---------------------------------------------------------------------------
def save_processed_data(df: pd.DataFrame, output_path: Path) -> None:
    """Save processed dataset to CSV with consistent formatting."""
    logger.info("Saving processed dataset to %s ...", output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    save_df = df.copy()

    # Format dates as YYYY-MM-DD
    for col in DATE_COLUMNS:
        if col in save_df.columns and pd.api.types.is_datetime64_any_dtype(save_df[col]):
            save_df[col] = save_df[col].dt.strftime("%Y-%m-%d")

    # Ensure integer types for integer-like columns
    int_cols = ["lead_time", "quantity", "delay_days", "inventory_level", "demand",
                "lead_time_outlier", "is_delayed", "inventory_shortage",
                "is_weekend_order", "order_year", "order_month", "order_quarter",
                "order_day_of_week"]
    for col in int_cols:
        if col in save_df.columns:
            save_df[col] = save_df[col].fillna(0).astype(int)

    save_df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info("Saved %d rows × %d columns", len(save_df), len(save_df.columns))


# ---------------------------------------------------------------------------
# Step 16 — Generate reports
# ---------------------------------------------------------------------------
def generate_reports(
    profile: dict[str, Any],
    stats: dict[str, Any],
    val_results: dict[str, bool],
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    input_path: Path,
    output_path: Path,
    val_report_path: Path,
    clean_report_path: Path,
) -> None:
    """Write validation and cleaning JSON reports."""
    val_report_path.parent.mkdir(parents=True, exist_ok=True)

    rows_before = profile["row_count"]
    rows_after = len(df_after)
    missing_before = profile["total_missing"]
    missing_after = int(df_after[df_after.columns.intersection(REQUIRED_COLUMNS)].isna().sum().sum())

    validation_status = "PASS" if all(val_results.values()) else "FAIL"

    validation_report = {
        "input_file": str(input_path),
        "output_file": str(output_path),
        "pipeline_run_at": datetime.now().isoformat(),
        "rows_before": rows_before,
        "rows_after": rows_after,
        "columns_before": profile["column_count"],
        "columns_after": len(df_after.columns),
        "missing_values_before": missing_before,
        "missing_values_after": missing_after,
        "duplicates_found": stats.get("duplicate_rows_found", 0),
        "duplicates_removed": stats.get("duplicate_rows_removed", 0),
        "invalid_dates_found": stats.get("invalid_dates_found", 0),
        "invalid_dates_fixed": stats.get("invalid_dates_fixed", 0),
        "negative_quantities_found": stats.get("negative_quantities_found", 0),
        "negative_quantities_fixed": stats.get("negative_quantities_fixed", 0),
        "abnormal_lead_times_found": stats.get("abnormal_lead_times_found", 0),
        "lead_times_corrected": stats.get("lead_times_corrected", 0),
        "invalid_categories_found": stats.get("invalid_categories_found", 0),
        "orphan_suppliers": stats.get("orphan_suppliers", 0),
        "orphan_products": stats.get("orphan_products", 0),
        "validation_checks": val_results,
        "validation_status": validation_status,
    }

    with open(val_report_path, "w", encoding="utf-8") as f:
        json.dump(validation_report, f, indent=2, default=str)
    logger.info("Validation report saved: %s", val_report_path)

    cleaning_report = {
        "pipeline_run_at": datetime.now().isoformat(),
        "rows_removed_total": rows_before - rows_after,
        "rows_retained": rows_after,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "missing_id_rows_removed": stats.get("missing_id_rows_removed", 0),
        "rows_removed_bad_dates": stats.get("rows_removed_bad_dates", 0),
        "orphan_suppliers_removed": stats.get("orphan_suppliers", 0),
        "orphan_products_removed": stats.get("orphan_products", 0),
        "missing_values_handled": {
            "categorical_filled_unknown": stats.get("missing_categorical_filled", {}),
            "numeric_imputed": stats.get("missing_numeric_imputed", {}),
        },
        "duplicate_records_removed": stats.get("duplicate_rows_removed", 0),
        "duplicate_shipment_ids_deduplicated": stats.get("duplicate_shipment_ids", 0),
        "invalid_dates_corrected": stats.get("invalid_dates_fixed", 0),
        "negative_quantities_corrected": stats.get("negative_quantities_fixed", 0),
        "numeric_corrections": stats.get("numeric_corrections", {}),
        "categorical_corrections": stats.get("categorical_corrections", {}),
        "lead_time_corrections": stats.get("lead_times_corrected", 0),
        "delay_days_corrections": stats.get("delay_days_corrected", 0),
        "coercion_errors": stats.get("coercion_errors", {}),
        "features_count_before": profile["column_count"],
        "features_count_after": len(df_after.columns),
        "features_added": stats.get("features_added", 0),
        "lead_time_outliers_flagged": stats.get("abnormal_lead_times_found", 0),
    }

    with open(clean_report_path, "w", encoding="utf-8") as f:
        json.dump(cleaning_report, f, indent=2, default=str)
    logger.info("Cleaning report saved: %s", clean_report_path)


# ---------------------------------------------------------------------------
# README generation
# ---------------------------------------------------------------------------
def write_readme(readme_path: Path, df: pd.DataFrame) -> None:
    """Write processed dataset README documentation."""
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    content = """\
# SupplyPrescript — Processed Dataset

## Pipeline

```
Raw CSV (data/synthetic/shipments.csv)
  ↓  Load & Schema Validation
  ↓  Initial Profiling
  ↓  Missing Value Handling
  ↓  Duplicate Removal
  ↓  Date Parsing & Validation
  ↓  Lead-Time Recalculation
  ↓  Negative Quantity Handling
  ↓  Numerical Value Validation
  ↓  Categorical Normalization
  ↓  Delay Recalculation
  ↓  Reference Validation (suppliers/products)
  ↓  Feature Engineering
  ↓  Final Validation
  ↓  Save (data/processed/shipments_processed.csv)
```

## Cleaning Rules

| Issue | Strategy |
|---|---|
| Missing critical IDs (`shipment_id`, `supplier_id`, `product_id`) | Row removed |
| Missing categorical fields (`origin`, `destination`, `priority`, `transport_mode`) | Filled with `"Unknown"` |
| Missing numeric fields (`quantity`, `unit_cost`, etc.) | Group-level median (by `supplier_id`), falling back to global median |
| Missing `order_date` | Row removed (cannot reconstruct) |
| Missing `expected_delivery_date` | Reconstructed from `order_date + lead_time` |
| Missing `actual_delivery_date` | Reconstructed from `expected_delivery_date + delay_days` |
| Duplicate rows | First valid record kept |
| Duplicate `shipment_id` | Most complete record kept |
| `expected_delivery_date < order_date` | Dates swapped |
| `actual_delivery_date < order_date` | `actual_delivery_date` set to `order_date` |
| `lead_time` inconsistent with dates | Recalculated from `actual_delivery_date - order_date` |
| `delay_days` inconsistent with dates | Recalculated from `max(0, actual − expected)` |
| `quantity < 0` | Sign-flip correction (data-entry error) |
| `quantity <= 0` | Imputed with product-level median |
| `unit_cost <= 0` | Imputed with product-level median |
| `shipping_cost < 0` | Absolute value taken |
| `inventory_level < 0` | Clipped to 0 |
| `demand < 0` | Absolute value taken |
| `supplier_reliability` as percentage (70–99) | Divided by 100 |
| `supplier_reliability` outside [0,1] | Clipped to [0,1] |
| `delay_days < 0` | Set to 0 |
| Invalid `transport_mode` | Mapped to canonical value or `"Unknown"` |
| Invalid `priority` | Mapped to canonical value or `"Unknown"` |
| Orphan `supplier_id` (not in suppliers.csv) | Row removed |
| Orphan `product_id` (not in products.csv) | Row removed |

## Engineered Features

| Feature | Description |
|---|---|
| `is_delayed` | 1 if `delay_days > 0`, else 0 |
| `delivery_status` | `"On Time"` or `"Delayed"` |
| `inventory_shortage` | 1 if `inventory_level < demand`, else 0 |
| `inventory_coverage_ratio` | `inventory_level / demand` (∞ when demand = 0) |
| `total_product_cost` | `quantity × unit_cost` |
| `total_cost` | `total_product_cost + shipping_cost` |
| `order_year` | Year extracted from `order_date` |
| `order_month` | Month (1–12) extracted from `order_date` |
| `order_quarter` | Quarter (1–4) extracted from `order_date` |
| `order_day_of_week` | Day-of-week (0=Monday, 6=Sunday) |
| `is_weekend_order` | 1 if order placed on Saturday or Sunday |
| `lead_time_category` | Tertile-based: `Short`, `Medium`, `Long` |
| `lead_time_outlier` | 1 if `lead_time` is a statistical IQR outlier |

## Data Leakage Warning

> **IMPORTANT**: The following fields represent **post-delivery outcomes**.
> They must **NOT** be used as predictive input features when building models
> that predict shipment outcomes **before** the actual delivery date.

| Field | Why it's a leakage risk |
|---|---|
| `actual_delivery_date` | Known only after delivery |
| `delay_days` | Derived from `actual_delivery_date` |
| `delivery_status` | Derived from `delay_days` |
| `is_delayed` | Derived from `delay_days` |
| `lead_time` | Recalculated from actual dates (post-delivery) |
| `lead_time_outlier` | Derived from `lead_time` |

Pre-delivery safe features include: `order_date`, `expected_delivery_date`,
`supplier_id`, `product_id`, `origin`, `destination`, `transport_mode`,
`priority`, `quantity`, `unit_cost`, `shipping_cost`, `supplier_reliability`,
`inventory_level`, `demand`, and all engineered date/cost features that do
not rely on actual delivery information.

## File Descriptions

| File | Description |
|---|---|
| `shipments_processed.csv` | Cleaned and feature-engineered shipment dataset |
| `validation_report.json` | Summary of validation checks and data-quality metrics |
| `cleaning_report.json` | Detailed record of all cleaning operations performed |
| `README.md` | This documentation file |
"""
    readme_path.write_text(content, encoding="utf-8")
    logger.info("README written: %s", readme_path)


# ---------------------------------------------------------------------------
# Main pipeline orchestrator
# ---------------------------------------------------------------------------
def run_pipeline(
    input_path: Path = DEFAULT_INPUT,
    suppliers_path: Path = DEFAULT_SUPPLIERS,
    products_path: Path = DEFAULT_PRODUCTS,
    output_path: Path = DEFAULT_OUTPUT,
    val_report_path: Path = DEFAULT_VAL_REPORT,
    clean_report_path: Path = DEFAULT_CLEAN_REPORT,
    readme_path: Path = DEFAULT_README,
) -> bool:
    """
    Execute the complete data pipeline.
    Returns True on success, False if final validation fails.
    """
    logger.info("=" * 60)
    logger.info("SupplyPrescript Data Pipeline — Day 3")
    logger.info("=" * 60)

    stats: dict[str, Any] = {}

    # 1. Load
    df = load_data(input_path)
    df_raw = df.copy()  # Keep for reporting

    # 2. Validate schema
    validate_schema(df)

    # 3. Profile (non-destructive)
    profile = profile_data(df)

    # 4. Coerce numeric types
    df = coerce_numeric_columns(df, stats)

    # 5. Handle missing values
    logger.info("Cleaning ...")
    logger.info("Missing Values Before Cleaning:")
    for col in REQUIRED_COLUMNS:
        n = int(df[col].isna().sum()) if col in df.columns else 0
        if n > 0:
            logger.info("  %s: %d", col, n)

    df = clean_missing_values(df, stats)

    # 6. Remove duplicates
    df = remove_duplicates(df, stats)

    # 7. Parse and validate dates
    df = clean_dates(df, stats)

    # 8. Handle lead times
    df = handle_abnormal_lead_times(df, stats)

    # 9. Numeric validation (includes negative quantity handling)
    df = clean_numeric_values(df, stats)

    # 10. Categorical normalization
    df = clean_categorical_values(df, stats)

    # 11. Recalculate derived fields (delay_days)
    df = recalculate_derived_fields(df, stats)

    # 12. Reference validation
    df = validate_references(df, suppliers_path, products_path, stats)

    logger.info("Cleaning complete.")

    # 13. Feature engineering
    df = engineer_features(df, stats)
    logger.info("Feature engineering complete.")

    # 14. Final validation
    val_results = validate_processed_data(df)
    validation_passed = all(val_results.values())

    if not validation_passed:
        failed = [k for k, v in val_results.items() if not v]
        logger.error("Pipeline cannot be marked successful — validation failed: %s", failed)
        # Still save reports even on failure
        generate_reports(
            profile, stats, val_results, df_raw, df,
            input_path, output_path,
            val_report_path, clean_report_path,
        )
        return False

    # 15. Save
    logger.info("Saving processed dataset ...")
    save_processed_data(df, output_path)

    # 16. Reports
    generate_reports(
        profile, stats, val_results, df_raw, df,
        input_path, output_path,
        val_report_path, clean_report_path,
    )
    write_readme(readme_path, df)

    # Summary
    logger.info("=" * 60)
    logger.info("Pipeline completed successfully.")
    logger.info("  Rows before : %d", profile["row_count"])
    logger.info("  Rows after  : %d", len(df))
    logger.info("  Columns before: %d", profile["column_count"])
    logger.info("  Columns after : %d", len(df.columns))
    logger.info("  Output: %s", output_path)
    logger.info("=" * 60)

    return True


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="SupplyPrescript Day 3 — Data Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to raw shipments CSV",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path for processed output CSV",
    )
    parser.add_argument(
        "--suppliers",
        type=Path,
        default=DEFAULT_SUPPLIERS,
        help="Path to suppliers reference CSV",
    )
    parser.add_argument(
        "--products",
        type=Path,
        default=DEFAULT_PRODUCTS,
        help="Path to products reference CSV",
    )
    args = parser.parse_args()

    success = run_pipeline(
        input_path=args.input,
        suppliers_path=args.suppliers,
        products_path=args.products,
        output_path=args.output,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
