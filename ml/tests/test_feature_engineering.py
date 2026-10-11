"""
Unit tests for ml/feature_engineering.py
========================================
Tests feature engineering derivations, target generation, causal historical delay,
distance calculations, season mapping, chronological splits, and pipeline artifacts.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.feature_config import (
    APPROVED_FEATURES,
    CLASSIFICATION_COLUMNS,
    CLASSIFICATION_TARGET,
    REGRESSION_COLUMNS,
    REGRESSION_TARGET,
    calculate_hub_distance_km,
)
from ml.feature_engineering import (
    calculate_historical_avg_delay,
    create_targets,
    derive_distance,
    derive_planned_lead_time,
    derive_season,
    run_feature_pipeline,
)


@pytest.fixture
def sample_shipments_df() -> pd.DataFrame:
    """Create a minimal synthetic shipment DataFrame for fast unit testing."""
    dates = pd.date_range("2024-01-01", periods=10, freq="7D")
    data = {
        "shipment_id": [f"SHIP{i:04d}" for i in range(10)],
        "supplier_id": ["SUP001"] * 5 + ["SUP002"] * 5,
        "product_id": [f"PROD{i:03d}" for i in range(10)],
        "origin": ["Mumbai", "Delhi", "Pune", "Bengaluru", "Chennai"] * 2,
        "destination": ["Delhi", "Mumbai", "Bengaluru", "Pune", "Kolkata"] * 2,
        "order_date": dates.strftime("%Y-%m-%d"),
        "expected_delivery_date": (dates + pd.Timedelta(days=7)).strftime("%Y-%m-%d"),
        "actual_delivery_date": [
            (dates[i] + pd.Timedelta(days=7 + (i % 3))).strftime("%Y-%m-%d")
            for i in range(10)
        ],
        "quantity": [100, 200, 150, 300, 250, 400, 120, 180, 220, 350],
        "unit_cost": [10.5, 20.0, 15.0, 30.0, 25.0, 40.0, 12.0, 18.0, 22.0, 35.0],
        "shipping_cost": [100.0, 150.0, 120.0, 200.0, 180.0, 250.0, 110.0, 140.0, 160.0, 220.0],
        "supplier_reliability": [0.95, 0.90, 0.92, 0.88, 0.94, 0.85, 0.89, 0.91, 0.93, 0.87],
        "inventory_level": [500, 600, 450, 700, 550, 800, 400, 520, 620, 750],
        "demand": [400, 500, 420, 650, 500, 750, 380, 480, 580, 700],
        "priority": ["High", "Medium", "Low", "Critical", "Medium"] * 2,
        "transport_mode": ["Road", "Rail", "Air", "Sea", "Road"] * 2,
    }
    return pd.DataFrame(data)


def test_derive_season():
    """Verify season mapping across all calendar months."""
    dates = pd.Series([
        "2024-01-15",  # Winter
        "2024-02-10",  # Winter
        "2024-03-20",  # Summer
        "2024-04-05",  # Summer
        "2024-05-18",  # Summer
        "2024-06-01",  # Monsoon
        "2024-07-14",  # Monsoon
        "2024-08-22",  # Monsoon
        "2024-09-30",  # Monsoon
        "2024-10-10",  # Post-Monsoon
        "2024-11-25",  # Post-Monsoon
        "2024-12-05",  # Winter
    ])
    seasons = derive_season(dates)
    expected = [
        "Winter", "Winter", "Summer", "Summer", "Summer",
        "Monsoon", "Monsoon", "Monsoon", "Monsoon",
        "Post-Monsoon", "Post-Monsoon", "Winter",
    ]
    assert list(seasons) == expected


def test_derive_distance_hubs():
    """Verify route distance between hubs matches Haversine formula with circuity."""
    mumbai_pune = calculate_hub_distance_km("Mumbai", "Pune")
    # Mumbai to Pune is ~120-170 km with circuity factor
    assert 100 < mumbai_pune < 250

    mumbai_delhi = calculate_hub_distance_km("Mumbai", "Delhi")
    # Mumbai to Delhi is ~1400 km
    assert 1200 < mumbai_delhi < 1800

    # Same city gets intra-city minimum
    assert calculate_hub_distance_km("Mumbai", "Mumbai") == 35.0

    # Series derivation
    origins = pd.Series(["Mumbai", "Delhi"])
    dests = pd.Series(["Pune", "Mumbai"])
    dists = derive_distance(origins, dests)
    assert len(dists) == 2
    assert (dists > 30).all()


def test_derive_planned_lead_time_no_leakage():
    """Verify planned lead time uses strictly expected delivery date - order date."""
    order = pd.Series(["2024-01-01", "2024-01-05"])
    expected = pd.Series(["2024-01-08", "2024-01-15"])
    plt = derive_planned_lead_time(order, expected)
    assert list(plt) == [7, 10]


def test_create_targets():
    """Verify delay_days and delayed targets calculation."""
    df = pd.DataFrame({
        "expected_delivery_date": ["2024-01-10", "2024-01-10", "2024-01-10"],
        "actual_delivery_date": ["2024-01-10", "2024-01-15", "2024-01-08"],  # on time, delayed 5, early 2
    })
    delay_days, delayed = create_targets(df)

    # Early delivery should be clipped to 0
    assert list(delay_days) == [0, 5, 0]
    assert list(delayed) == [0, 1, 0]


def test_historical_avg_delay_strictly_causal():
    """
    Critical Test: verify that historical_avg_delay uses only prior shipments.
    Row 0 for a supplier must receive the fallback value.
    Row 1 must reflect ONLY row 0's delay.
    Row 2 must reflect ONLY (row 0 + row 1) / 2.
    """
    df = pd.DataFrame({
        "order_date": pd.date_range("2024-01-01", periods=4, freq="D"),
        "supplier_id": ["SUP001", "SUP001", "SUP001", "SUP001"],
        "delay_days": [2, 4, 6, 8],
    })
    hist_delay = calculate_historical_avg_delay(
        df_sorted=df,
        supplier_col="supplier_id",
        delay_col="delay_days",
        fallback_value=0.0,
    )

    # Row 0: no prior history -> fallback 0.0
    assert hist_delay.iloc[0] == 0.0
    # Row 1: only row 0 (delay=2) -> 2.0
    assert hist_delay.iloc[1] == 2.0
    # Row 2: (2 + 4) / 2 = 3.0
    assert hist_delay.iloc[2] == 3.0
    # Row 3: (2 + 4 + 6) / 3 = 4.0
    assert hist_delay.iloc[3] == 4.0


def test_no_future_leakage_in_historical_avg_delay():
    """
    Verify changing future shipment delay NEVER affects earlier historical features.
    """
    df_orig = pd.DataFrame({
        "order_date": pd.date_range("2024-01-01", periods=3, freq="D"),
        "supplier_id": ["SUP001", "SUP001", "SUP001"],
        "delay_days": [2, 4, 10],
    })
    res_orig = calculate_historical_avg_delay(df_orig, fallback_value=0.0)

    # Mutate the 3rd shipment's delay to an extreme value (e.g. 500)
    df_mutated = df_orig.copy()
    df_mutated.loc[2, "delay_days"] = 500

    res_mutated = calculate_historical_avg_delay(df_mutated, fallback_value=0.0)

    # Row 0 and Row 1 MUST be strictly identical
    assert res_orig.iloc[0] == res_mutated.iloc[0]
    assert res_orig.iloc[1] == res_mutated.iloc[1]
    # Row 2 still uses only row 0 and 1, so row 2's feature is also identical!
    assert res_orig.iloc[2] == res_mutated.iloc[2]


def test_run_feature_pipeline_end_to_end(sample_shipments_df):
    """
    Execute complete pipeline on temporary directory fixture and verify all artifacts exist.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_csv = tmp_path / "shipments_input.csv"
        sample_shipments_df.to_csv(input_csv, index=False)

        reg_dir = tmp_path / "features" / "regression"
        cls_dir = tmp_path / "features" / "classification"
        meta_dir = tmp_path / "features" / "metadata"

        result = run_feature_pipeline(
            input_path=input_csv,
            regression_dir=reg_dir,
            classification_dir=cls_dir,
            metadata_dir=meta_dir,
        )

        assert result["status"] == "SUCCESS"
        assert result["total_rows"] == 10
        assert result["features_count"] == len(APPROVED_FEATURES)

        # Check regression files
        assert (reg_dir / "train.csv").exists()
        assert (reg_dir / "validation.csv").exists()
        assert (reg_dir / "test.csv").exists()

        # Check classification files
        assert (cls_dir / "train.csv").exists()
        assert (cls_dir / "validation.csv").exists()
        assert (cls_dir / "test.csv").exists()

        # Check metadata files
        assert (meta_dir / "feature_schema.json").exists()
        assert (meta_dir / "feature_report.json").exists()
        assert (meta_dir / "split_metadata.json").exists()
        assert (meta_dir / "leakage_report.json").exists()
        assert (meta_dir / "preprocessor.joblib").exists()

        # Verify saved dataset columns
        reg_train = pd.read_csv(reg_dir / "train.csv")
        assert list(reg_train.columns) == REGRESSION_COLUMNS

        cls_train = pd.read_csv(cls_dir / "train.csv")
        assert list(cls_train.columns) == CLASSIFICATION_COLUMNS
