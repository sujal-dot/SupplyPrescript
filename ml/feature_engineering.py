"""
SupplyPrescript — Day 6 Feature Engineering Pipeline
====================================================
Transforms historical processed shipment data into validated, leak-free,
model-ready feature matrices for delay prediction (regression and classification).

Usage:
    python -m ml.feature_engineering
    python -m ml.feature_engineering --input data/processed/shipments_processed.csv
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

from ml.feature_config import (
    APPROVED_FEATURES,
    CATEGORICAL_FEATURES,
    CLASSIFICATION_COLUMNS,
    CLASSIFICATION_DIR,
    CLASSIFICATION_TARGET,
    DEFAULT_INPUT_PATH,
    EXPECTED_DELIVERY_DATE_COL,
    FEATURE_REPORT_PATH,
    FEATURE_SCHEMA_PATH,
    FEATURES_DIR,
    INTRA_CITY_MIN_DISTANCE_KM,
    LEAKAGE_COLUMNS,
    LEAKAGE_REPORT_PATH,
    METADATA_DIR,
    NUMERICAL_FEATURES,
    ORDER_DATE_COL,
    PREPROCESSOR_ARTIFACT_PATH,
    RANDOM_SEED,
    REGRESSION_COLUMNS,
    REGRESSION_DIR,
    REGRESSION_TARGET,
    SEASON_MONTH_MAP,
    SHIPMENT_ID_COL,
    SPLIT_METADATA_PATH,
    SUPPLIER_ID_COL,
    TEST_RATIO,
    TRAIN_RATIO,
    VAL_RATIO,
    calculate_hub_distance_km,
)
from ml.feature_validation import (
    compile_feature_report,
    validate_categorical_features,
    validate_numerical_features,
    validate_targets,
)
from ml.leakage_checks import (
    check_feature_matrix_for_leakage,
    generate_leakage_report,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ml.feature_engineering")


def load_dataset(input_path: Path) -> pd.DataFrame:
    """Load processed historical shipment dataset with safe date parsing."""
    logger.info("Loading dataset from: %s", input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input dataset file not found: {input_path}")

    df = pd.read_csv(input_path, low_memory=False)
    logger.info("Loaded %d rows × %d columns", len(df), len(df.columns))
    return df


def derive_season(order_date_series: pd.Series) -> pd.Series:
    """
    Derive Indian meteorological season from order_date:
    - Winter: Dec, Jan, Feb
    - Summer: Mar, Apr, May
    - Monsoon: Jun, Jul, Aug, Sep
    - Post-Monsoon: Oct, Nov
    """
    dt_series = pd.to_datetime(order_date_series)
    return dt_series.dt.month.map(SEASON_MONTH_MAP).fillna("Winter").astype(str)


def derive_distance(origins: pd.Series, destinations: pd.Series) -> pd.Series:
    """
    Calculate estimated highway route distance (km) between origin and destination hubs.
    Uses Haversine formula + 1.25 circuity factor.
    """
    distances = [
        calculate_hub_distance_km(orig, dest)
        for orig, dest in zip(origins, destinations)
    ]
    return pd.Series(distances, index=origins.index, dtype=float)


def derive_planned_lead_time(order_dates: pd.Series, expected_dates: pd.Series) -> pd.Series:
    """
    Calculate planned lead time known at order placement:
    planned_lead_time = (expected_delivery_date - order_date).days
    Strictly avoids using actual delivery date to prevent target leakage.
    """
    dt_order = pd.to_datetime(order_dates)
    dt_expected = pd.to_datetime(expected_dates)
    lead_time_days = (dt_expected - dt_order).dt.days
    # Minimum 1 day lead time safety
    return lead_time_days.clip(lower=1).astype(int)


def calculate_historical_avg_delay(
    df_sorted: pd.DataFrame,
    supplier_col: str = SUPPLIER_ID_COL,
    delay_col: str = REGRESSION_TARGET,
    fallback_value: float = 0.0,
) -> pd.Series:
    """
    Compute supplier historical average delay using strictly earlier shipments.
    - Dataset MUST be pre-sorted chronologically.
    - Uses shift(1).expanding().mean() grouped by supplier.
    - Current shipment's delay is NEVER included.
    - Fallback is applied for a supplier's initial shipment.
    """
    # Shift delay by 1 within supplier group so current row is excluded
    shifted_expanding_mean = (
        df_sorted.groupby(supplier_col)[delay_col]
        .transform(lambda s: s.shift(1).expanding().mean())
    )
    # Fill suppliers with no prior history using the fitted fallback
    return shifted_expanding_mean.fillna(fallback_value).round(4)


def create_targets(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """
    Construct regression and classification targets.
    - delay_days: max(0, actual_delivery_date - expected_delivery_date)
    - delayed: 1 if delay_days > 0 else 0
    """
    dt_actual = pd.to_datetime(df["actual_delivery_date"])
    dt_expected = pd.to_datetime(df["expected_delivery_date"])
    delay_days = (dt_actual - dt_expected).dt.days.clip(lower=0).astype(int)
    delay_days.name = REGRESSION_TARGET
    delayed = (delay_days > 0).astype(int)
    delayed.name = CLASSIFICATION_TARGET
    return delay_days, delayed


def build_feature_schema() -> List[Dict[str, Any]]:
    """Build detailed schema documentation for all approved features."""
    schema = [
        {
            "feature_name": "supplier_reliability",
            "type": "numeric",
            "data_type": "float64",
            "source": "suppliers / historical performance",
            "derivation": "Direct recorded supplier reliability score in [0.0, 1.0]",
            "availability": "Available at order creation",
            "approved_for_training": True,
            "business_meaning": "Supplier historical score indicating baseline reliability.",
            "missing_value_handling": "Imputed via group/global median if missing.",
        },
        {
            "feature_name": "historical_avg_delay",
            "type": "numeric",
            "data_type": "float64",
            "source": "historical shipment records (causal prior-only)",
            "derivation": "Expanding mean of delay_days from previous shipments of the supplier (shift(1))",
            "availability": "Available at order creation (strictly prior shipments)",
            "approved_for_training": True,
            "business_meaning": "Supplier empirical track record of average delay days up to this order.",
            "missing_value_handling": "Neutral training fallback (0.0 days) for suppliers with no prior history.",
        },
        {
            "feature_name": "lead_time",
            "type": "numeric",
            "data_type": "int64",
            "source": "order scheduling / expected_delivery_date",
            "derivation": "(expected_delivery_date - order_date).days (Planned lead time)",
            "availability": "Available at order creation",
            "approved_for_training": True,
            "business_meaning": "Planned delivery transit days scheduled at order placement.",
            "missing_value_handling": "Calculated deterministically from order and expected delivery dates.",
        },
        {
            "feature_name": "inventory_level",
            "type": "numeric",
            "data_type": "int64",
            "source": "warehouse ERP inventory records",
            "derivation": "Inventory units on hand at origin/distribution node at order time",
            "availability": "Available at order creation",
            "approved_for_training": True,
            "business_meaning": "Stock availability to fulfill demand and absorb supply shocks.",
            "missing_value_handling": "Non-negative integer validation.",
        },
        {
            "feature_name": "demand",
            "type": "numeric",
            "data_type": "int64",
            "source": "sales forecasting / customer order demand",
            "derivation": "Projected market demand for product SKU at order placement",
            "availability": "Available at order creation",
            "approved_for_training": True,
            "business_meaning": "Demand pressure on the supply chain node.",
            "missing_value_handling": "Non-negative integer validation.",
        },
        {
            "feature_name": "quantity",
            "type": "numeric",
            "data_type": "int64",
            "source": "shipment purchase order",
            "derivation": "Ordered units in shipment",
            "availability": "Available at order creation",
            "approved_for_training": True,
            "business_meaning": "Batch size of the shipment.",
            "missing_value_handling": "Strictly positive integer validation.",
        },
        {
            "feature_name": "shipping_cost",
            "type": "numeric",
            "data_type": "float64",
            "source": "carrier freight booking rate",
            "derivation": "Known contracted shipping freight cost",
            "availability": "Available at order creation / dispatch booking",
            "approved_for_training": True,
            "business_meaning": "Logistics expenditure allocated to shipment.",
            "missing_value_handling": "Non-negative float validation.",
        },
        {
            "feature_name": "distance",
            "type": "numeric",
            "data_type": "float64",
            "source": "origin and destination geographical coordinates",
            "derivation": "Haversine great-circle formula between hubs + 1.25 highway circuity factor",
            "availability": "Available at order creation",
            "approved_for_training": True,
            "business_meaning": "Estimated route distance in kilometers between origin and destination.",
            "missing_value_handling": "Fallback to intra-city minimum (35 km) if hubs match or coordinates missing.",
        },
        {
            "feature_name": "transport_mode",
            "type": "categorical",
            "data_type": "object / string",
            "source": "freight contract logistics channel",
            "derivation": "Modality chosen: Road, Rail, Air, or Sea",
            "availability": "Available at order creation",
            "approved_for_training": True,
            "business_meaning": "Logistical mode of transit.",
            "missing_value_handling": "One-hot encoded with handle_unknown='ignore'.",
        },
        {
            "feature_name": "season",
            "type": "categorical",
            "data_type": "object / string",
            "source": "order_date month calendar",
            "derivation": "Indian seasonal mapping (Winter, Summer, Monsoon, Post-Monsoon)",
            "availability": "Available at order creation",
            "approved_for_training": True,
            "business_meaning": "Weather and seasonal monsoon demand cycle.",
            "missing_value_handling": "Derived deterministically from order_date.",
        },
        {
            "feature_name": "priority",
            "type": "categorical",
            "data_type": "object / string",
            "source": "order dispatch urgency specification",
            "derivation": "Urgency rating: Low, Medium, High, or Critical",
            "availability": "Available at order creation",
            "approved_for_training": True,
            "business_meaning": "Priority level influencing carrier dispatch speed.",
            "missing_value_handling": "One-hot encoded with handle_unknown='ignore'.",
        },
    ]
    return schema


def run_feature_pipeline(
    input_path: Path = DEFAULT_INPUT_PATH,
    regression_dir: Path = REGRESSION_DIR,
    classification_dir: Path = CLASSIFICATION_DIR,
    metadata_dir: Path = METADATA_DIR,
) -> Dict[str, Any]:
    """
    Execute complete end-to-end Day 6 Feature Engineering Pipeline.
    """
    logger.info("=" * 65)
    logger.info("SupplyPrescript ML Pipeline — Day 6: Feature Engineering")
    logger.info("=" * 65)

    regression_dir.mkdir(parents=True, exist_ok=True)
    classification_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    df_raw = load_dataset(input_path)
    initial_rows = len(df_raw)

    # 2. Filter records with unusable dates / targets
    date_cols = [ORDER_DATE_COL, EXPECTED_DELIVERY_DATE_COL, "actual_delivery_date"]
    valid_mask = df_raw[date_cols].notna().all(axis=1)
    rejected_rows_count = int((~valid_mask).sum())
    if rejected_rows_count > 0:
        logger.warning("Rejected %d rows due to missing essential date values.", rejected_rows_count)

    df = df_raw[valid_mask].copy()

    # 3. Targets generation
    delay_days, delayed = create_targets(df)
    df[REGRESSION_TARGET] = delay_days
    df[CLASSIFICATION_TARGET] = delayed

    # 4. Feature derivations (leakage-safe)
    logger.info("Deriving planned lead time, seasons, and hub transit distances...")
    df["lead_time"] = derive_planned_lead_time(df[ORDER_DATE_COL], df[EXPECTED_DELIVERY_DATE_COL])
    df["season"] = derive_season(df[ORDER_DATE_COL])
    df["distance"] = derive_distance(df["origin"], df["destination"])

    # 5. Strict Chronological Ordering
    logger.info("Sorting records chronologically by order_date and shipment_id...")
    df[ORDER_DATE_COL] = pd.to_datetime(df[ORDER_DATE_COL])
    df = df.sort_values(by=[ORDER_DATE_COL, SHIPMENT_ID_COL]).reset_index(drop=True)

    # 6. Chronological Train / Validation / Test Splits (70% / 15% / 15%)
    n_total = len(df)
    n_train = int(n_total * TRAIN_RATIO)
    n_val = int(n_total * (TRAIN_RATIO + VAL_RATIO))

    train_slice = slice(0, n_train)
    val_slice = slice(n_train, n_val)
    test_slice = slice(n_val, n_total)

    logger.info(
        "Chronological splits: Train=%d (70%%), Val=%d (15%%), Test=%d (15%%)",
        n_train, n_val - n_train, n_total - n_val,
    )

    # 7. Time-Aware Historical Average Delay (strictly causal, prior shipments only)
    # Fit fallback on training split only!
    train_delay_series = df.iloc[train_slice][REGRESSION_TARGET]
    fitted_fallback_delay = float(train_delay_series.median())
    logger.info("Fitted historical delay fallback on training set: %.4f days", fitted_fallback_delay)

    df["historical_avg_delay"] = calculate_historical_avg_delay(
        df_sorted=df,
        supplier_col=SUPPLIER_ID_COL,
        delay_col=REGRESSION_TARGET,
        fallback_value=fitted_fallback_delay,
    )

    # 8. Separate Feature Matrix X and Targets
    X_all = df[APPROVED_FEATURES].copy()

    X_train = X_all.iloc[train_slice].copy().reset_index(drop=True)
    X_val = X_all.iloc[val_slice].copy().reset_index(drop=True)
    X_test = X_all.iloc[test_slice].copy().reset_index(drop=True)

    y_reg_train = df.iloc[train_slice][REGRESSION_TARGET].reset_index(drop=True)
    y_reg_val = df.iloc[val_slice][REGRESSION_TARGET].reset_index(drop=True)
    y_reg_test = df.iloc[test_slice][REGRESSION_TARGET].reset_index(drop=True)

    y_cls_train = df.iloc[train_slice][CLASSIFICATION_TARGET].reset_index(drop=True)
    y_cls_val = df.iloc[val_slice][CLASSIFICATION_TARGET].reset_index(drop=True)
    y_cls_test = df.iloc[test_slice][CLASSIFICATION_TARGET].reset_index(drop=True)

    # 9. Fit Preprocessing Pipeline (Scikit-Learn ColumnTransformer) on Train ONLY
    logger.info("Fitting Scikit-Learn ColumnTransformer on training features only...")
    preprocessor = ColumnTransformer(
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
    preprocessor.fit(X_train)

    # Save fitted preprocessor
    preprocessor_path = metadata_dir / "preprocessor.joblib"
    joblib.dump(preprocessor, preprocessor_path)
    logger.info("Saved fitted preprocessor to: %s", preprocessor_path)

    # 10. Run Strict Feature Validation & Leakage Checks
    logger.info("Running feature validations and data leakage audits...")
    validate_numerical_features(X_train)
    validate_numerical_features(X_val)
    validate_numerical_features(X_test)

    validate_categorical_features(X_train)
    validate_categorical_features(X_val)
    validate_categorical_features(X_test)

    validate_targets(df)

    # Leakage checks
    check_feature_matrix_for_leakage(X_train)
    check_feature_matrix_for_leakage(X_val)
    check_feature_matrix_for_leakage(X_test)

    # 11. Compile Datasets for Saving
    reg_train = pd.concat([X_train, y_reg_train], axis=1)[REGRESSION_COLUMNS]
    reg_val = pd.concat([X_val, y_reg_val], axis=1)[REGRESSION_COLUMNS]
    reg_test = pd.concat([X_test, y_reg_test], axis=1)[REGRESSION_COLUMNS]

    cls_train = pd.concat([X_train, y_cls_train], axis=1)[CLASSIFICATION_COLUMNS]
    cls_val = pd.concat([X_val, y_cls_val], axis=1)[CLASSIFICATION_COLUMNS]
    cls_test = pd.concat([X_test, y_cls_test], axis=1)[CLASSIFICATION_COLUMNS]

    # Save Regression Datasets
    reg_train_path = regression_dir / "train.csv"
    reg_val_path = regression_dir / "validation.csv"
    reg_test_path = regression_dir / "test.csv"

    reg_train.to_csv(reg_train_path, index=False)
    reg_val.to_csv(reg_val_path, index=False)
    reg_test.to_csv(reg_test_path, index=False)
    logger.info("Saved regression datasets: %s, %s, %s", reg_train_path.name, reg_val_path.name, reg_test_path.name)

    # Save Classification Datasets
    cls_train_path = classification_dir / "train.csv"
    cls_val_path = classification_dir / "validation.csv"
    cls_test_path = classification_dir / "test.csv"

    cls_train.to_csv(cls_train_path, index=False)
    cls_val.to_csv(cls_val_path, index=False)
    cls_test.to_csv(cls_test_path, index=False)
    logger.info("Saved classification datasets: %s, %s, %s", cls_train_path.name, cls_val_path.name, cls_test_path.name)

    # 12. Generate and Save Metadata Reports
    date_min = df[ORDER_DATE_COL].min().strftime("%Y-%m-%d")
    date_max = df[ORDER_DATE_COL].max().strftime("%Y-%m-%d")

    # Feature Schema JSON
    feature_schema_data = {
        "schema_version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "input_dataset": str(input_path),
        "approved_feature_count": len(APPROVED_FEATURES),
        "features": build_feature_schema(),
        "targets": [
            {
                "target_name": REGRESSION_TARGET,
                "task": "regression",
                "type": "numeric",
                "data_type": "int64",
                "derivation": "max(0, actual_delivery_date - expected_delivery_date)",
                "business_meaning": "Non-negative delay in days (0 indicates on-time arrival).",
            },
            {
                "target_name": CLASSIFICATION_TARGET,
                "task": "classification",
                "type": "binary",
                "data_type": "int64",
                "derivation": "1 if delay_days > 0 else 0",
                "business_meaning": "Binary delay status (0 = On-Time, 1 = Delayed).",
            },
        ],
    }
    schema_path = metadata_dir / "feature_schema.json"
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(feature_schema_data, f, indent=2)
    logger.info("Saved feature schema to: %s", schema_path)

    # Split Metadata JSON
    split_metadata = {
        "generated_at": datetime.now().isoformat(),
        "total_rows": n_total,
        "split_ratios": {
            "train": TRAIN_RATIO,
            "validation": VAL_RATIO,
            "test": TEST_RATIO,
        },
        "split_counts": {
            "train": len(X_train),
            "validation": len(X_val),
            "test": len(X_test),
        },
        "chronological_boundaries": {
            "train": {
                "start_order_date": df.iloc[train_slice][ORDER_DATE_COL].min().strftime("%Y-%m-%d"),
                "end_order_date": df.iloc[train_slice][ORDER_DATE_COL].max().strftime("%Y-%m-%d"),
            },
            "validation": {
                "start_order_date": df.iloc[val_slice][ORDER_DATE_COL].min().strftime("%Y-%m-%d"),
                "end_order_date": df.iloc[val_slice][ORDER_DATE_COL].max().strftime("%Y-%m-%d"),
            },
            "test": {
                "start_order_date": df.iloc[test_slice][ORDER_DATE_COL].min().strftime("%Y-%m-%d"),
                "end_order_date": df.iloc[test_slice][ORDER_DATE_COL].max().strftime("%Y-%m-%d"),
            },
        },
        "fitted_fallback_delay": fitted_fallback_delay,
    }
    split_meta_path = metadata_dir / "split_metadata.json"
    with open(split_meta_path, "w", encoding="utf-8") as f:
        json.dump(split_metadata, f, indent=2)
    logger.info("Saved split metadata to: %s", split_meta_path)

    # Leakage Report JSON
    leakage_report = generate_leakage_report(X_train, X_val, X_test)
    leakage_rep_path = metadata_dir / "leakage_report.json"
    with open(leakage_rep_path, "w", encoding="utf-8") as f:
        json.dump(leakage_report, f, indent=2)
    logger.info("Saved leakage report to: %s", leakage_rep_path)

    # Feature Quality Report JSON
    df_engineered = pd.concat([X_all, df[[REGRESSION_TARGET, CLASSIFICATION_TARGET]]], axis=1)
    feature_report = compile_feature_report(
        df_raw=df_raw,
        df_features=df_engineered,
        train_df=reg_train,
        val_df=reg_val,
        test_df=reg_test,
        rejected_rows_count=rejected_rows_count,
        date_min=date_min,
        date_max=date_max,
    )
    feature_rep_path = metadata_dir / "feature_report.json"
    with open(feature_rep_path, "w", encoding="utf-8") as f:
        json.dump(feature_report, f, indent=2)
    logger.info("Saved feature quality report to: %s", feature_rep_path)

    # Audit Trail CSV (maps shipment_id and dates to split for tracing)
    audit_df = pd.DataFrame({
        "shipment_id": df[SHIPMENT_ID_COL],
        "supplier_id": df[SUPPLIER_ID_COL],
        "product_id": df["product_id"],
        "order_date": df[ORDER_DATE_COL].dt.strftime("%Y-%m-%d"),
        "expected_delivery_date": df[EXPECTED_DELIVERY_DATE_COL],
        "actual_delivery_date": df["actual_delivery_date"],
        "delay_days": df[REGRESSION_TARGET],
        "delayed": df[CLASSIFICATION_TARGET],
        "split": ["train"] * n_train + ["validation"] * (n_val - n_train) + ["test"] * (n_total - n_val),
    })
    audit_path = metadata_dir / "split_audit.csv"
    audit_df.to_csv(audit_path, index=False)
    logger.info("Saved split audit trail to: %s", audit_path)

    logger.info("=" * 65)
    logger.info("Day 6 Feature Engineering Pipeline Completed Successfully!")
    logger.info("  Valid Rows Processed: %d", n_total)
    logger.info("  Approved Features:    %d", len(APPROVED_FEATURES))
    logger.info("  Train / Val / Test:   %d / %d / %d", len(X_train), len(X_val), len(X_test))
    logger.info("  Outputs generated in: %s", FEATURES_DIR)
    logger.info("=" * 65)

    return {
        "status": "SUCCESS",
        "total_rows": n_total,
        "features_count": len(APPROVED_FEATURES),
        "train_rows": len(X_train),
        "val_rows": len(X_val),
        "test_rows": len(X_test),
        "leakage_status": leakage_report["status"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SupplyPrescript Phase 3 Day 6 — Feature Engineering Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to input processed shipments CSV",
    )
    args = parser.parse_args()

    result = run_feature_pipeline(input_path=args.input)
    if result["status"] != "SUCCESS":
        sys.exit(1)


if __name__ == "__main__":
    main()
