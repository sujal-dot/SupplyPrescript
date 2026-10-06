"""
Unit tests for data/data_pipeline.py — Day 3 Data Pipeline

Tests use small in-memory DataFrames to avoid processing all 15,000 records
on every test run. The pipeline functions are tested individually.
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so we can import the pipeline module
# ---------------------------------------------------------------------------
_TESTS_DIR = Path(__file__).resolve().parent        # tests/data/
_PROJECT_ROOT = _TESTS_DIR.parent.parent             # SupplyPrescript/
_DATA_DIR = _PROJECT_ROOT / "data"

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(_DATA_DIR))

import importlib.util

_pipeline_path = _DATA_DIR / "data_pipeline.py"
spec = importlib.util.spec_from_file_location("data_pipeline", str(_pipeline_path))
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_base_df(n: int = 5) -> pd.DataFrame:
    """Create a minimal valid shipment DataFrame for testing."""
    today = pd.Timestamp("2024-01-15")
    expected = today + pd.Timedelta(days=7)
    actual = today + pd.Timedelta(days=7)

    rows = []
    for i in range(n):
        rows.append({
            "shipment_id": f"SHIP{i + 1:06d}",
            "supplier_id": f"SUP00{(i % 5) + 1}",
            "product_id": f"PROD00{(i % 10) + 1}",
            "origin": "Mumbai",
            "destination": "Delhi",
            "order_date": today,
            "expected_delivery_date": expected,
            "actual_delivery_date": actual,
            "lead_time": 7,
            "quantity": 100 + i * 10,
            "unit_cost": 50.0 + i,
            "shipping_cost": 200.0,
            "supplier_reliability": 0.90 + i * 0.01,
            "inventory_level": 500,
            "demand": 400,
            "priority": "Medium",
            "transport_mode": "Road",
            "delay_days": 0,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 1. Schema validation
# ---------------------------------------------------------------------------
class TestSchemaValidation:

    def test_valid_schema_passes(self):
        """All required columns present → no exit."""
        df = make_base_df()
        # Should not raise SystemExit
        pipeline.validate_schema(df)

    def test_missing_column_raises(self, monkeypatch):
        """Missing required column → sys.exit(1)."""
        df = make_base_df().drop(columns=["quantity"])
        with pytest.raises(SystemExit) as exc_info:
            pipeline.validate_schema(df)
        assert exc_info.value.code == 1

    def test_all_required_columns_checked(self, monkeypatch):
        """Each required column individually triggers failure if missing."""
        for col in pipeline.REQUIRED_COLUMNS:
            df = make_base_df()
            df = df.drop(columns=[col])
            with pytest.raises(SystemExit):
                pipeline.validate_schema(df)


# ---------------------------------------------------------------------------
# 2. Duplicate detection
# ---------------------------------------------------------------------------
class TestDuplicateDetection:

    def test_no_duplicates_unchanged(self):
        df = make_base_df(5)
        stats: dict = {}
        result = pipeline.remove_duplicates(df, stats)
        assert len(result) == 5
        assert stats["duplicate_rows_found"] == 0

    def test_exact_duplicate_rows_removed(self):
        df = make_base_df(3)
        df_with_dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)
        stats: dict = {}
        result = pipeline.remove_duplicates(df_with_dup, stats)
        assert stats["duplicate_rows_found"] == 1
        assert len(result) == 3

    def test_duplicate_shipment_id_deduped(self):
        df = make_base_df(3)
        # Create a row with a duplicate shipment_id but different content
        extra = df.iloc[0].copy()
        extra["quantity"] = 9999
        df_dup = pd.concat([df, pd.DataFrame([extra])], ignore_index=True)
        assert df_dup["shipment_id"].duplicated().any()
        stats: dict = {}
        result = pipeline.remove_duplicates(df_dup, stats)
        assert not result["shipment_id"].duplicated().any()
        assert stats["duplicate_shipment_ids"] >= 1


# ---------------------------------------------------------------------------
# 3. Negative quantity handling
# ---------------------------------------------------------------------------
class TestNegativeQuantities:

    def test_negative_quantity_corrected(self):
        df = make_base_df(3)
        df.loc[0, "quantity"] = -50
        stats: dict = {}
        result = pipeline.clean_numeric_values(df, stats)
        assert result.loc[0, "quantity"] > 0
        assert stats["negative_quantities_found"] == 1
        assert stats["negative_quantities_fixed"] == 1

    def test_all_quantities_positive_after_cleaning(self):
        df = make_base_df(5)
        df["quantity"] = [-10, -5, 0, 50, 100]
        stats: dict = {}
        result = pipeline.clean_numeric_values(df, stats)
        assert (result["quantity"] > 0).all()

    def test_zero_quantity_imputed(self):
        df = make_base_df(5)
        df.loc[2, "quantity"] = 0
        stats: dict = {}
        result = pipeline.clean_numeric_values(df, stats)
        assert result.loc[2, "quantity"] > 0


# ---------------------------------------------------------------------------
# 4. Invalid date handling
# ---------------------------------------------------------------------------
class TestDateHandling:

    def test_valid_dates_pass_unchanged(self):
        df = make_base_df(3)
        # Already datetime
        df["order_date"] = pd.to_datetime("2024-01-01")
        df["expected_delivery_date"] = pd.to_datetime("2024-01-08")
        df["actual_delivery_date"] = pd.to_datetime("2024-01-08")
        stats: dict = {}
        result = pipeline.clean_dates(df, stats)
        assert result["order_date"].notna().all()
        assert result["expected_delivery_date"].notna().all()

    def test_expected_before_order_swapped(self):
        df = make_base_df(2)
        # Set expected before order — should be swapped
        df.loc[0, "order_date"] = pd.Timestamp("2024-01-10")
        df.loc[0, "expected_delivery_date"] = pd.Timestamp("2024-01-05")
        df.loc[0, "actual_delivery_date"] = pd.Timestamp("2024-01-15")
        stats: dict = {}
        result = pipeline.clean_dates(df, stats)
        # After swap, order_date should be <= expected_delivery_date
        assert (result["order_date"] <= result["expected_delivery_date"]).all()

    def test_actual_before_order_fixed(self):
        df = make_base_df(2)
        df.loc[0, "order_date"] = pd.Timestamp("2024-01-10")
        df.loc[0, "actual_delivery_date"] = pd.Timestamp("2024-01-05")
        stats: dict = {}
        result = pipeline.clean_dates(df, stats)
        assert (result["order_date"] <= result["actual_delivery_date"]).all()

    def test_missing_order_date_removes_row(self):
        df = make_base_df(3)
        df.loc[1, "order_date"] = pd.NaT
        stats: dict = {}
        result = pipeline.clean_dates(df, stats)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# 5. Lead-time recalculation
# ---------------------------------------------------------------------------
class TestLeadTimeRecalculation:

    def test_lead_time_corrected_from_dates(self):
        df = make_base_df(3)
        df["order_date"] = pd.Timestamp("2024-01-01")
        df["actual_delivery_date"] = pd.Timestamp("2024-01-15")
        df["lead_time"] = 99  # Wrong value
        stats: dict = {}
        result = pipeline.handle_abnormal_lead_times(df, stats)
        assert (result["lead_time"] == 14).all()
        assert stats["lead_times_corrected"] == 3

    def test_lead_time_outlier_flagged(self):
        df = make_base_df(10)
        # Give one row an extreme lead time
        df.loc[0, "order_date"] = pd.Timestamp("2024-01-01")
        df.loc[0, "actual_delivery_date"] = pd.Timestamp("2025-01-01")
        df["lead_time"] = (df["actual_delivery_date"] - df["order_date"]).dt.days
        stats: dict = {}
        result = pipeline.handle_abnormal_lead_times(df, stats)
        assert "lead_time_outlier" in result.columns
        # The extreme row should be flagged
        assert result["lead_time_outlier"].sum() >= 1

    def test_lead_time_outlier_not_deleted(self):
        """Statistical outliers should be flagged but NOT removed."""
        df = make_base_df(10)
        df.loc[0, "lead_time"] = 1000  # Extreme outlier
        stats: dict = {}
        result = pipeline.handle_abnormal_lead_times(df, stats)
        # All rows still present
        assert len(result) == 10


# ---------------------------------------------------------------------------
# 6. Delay recalculation
# ---------------------------------------------------------------------------
class TestDelayRecalculation:

    def test_delay_recalculated_from_dates(self):
        df = make_base_df(3)
        df["expected_delivery_date"] = pd.Timestamp("2024-01-10")
        df["actual_delivery_date"] = pd.Timestamp("2024-01-15")
        df["delay_days"] = 99  # Wrong stored value
        stats: dict = {}
        result = pipeline.recalculate_derived_fields(df, stats)
        assert (result["delay_days"] == 5).all()
        assert stats["delay_days_corrected"] == 3

    def test_no_delay_clipped_to_zero(self):
        df = make_base_df(2)
        df["expected_delivery_date"] = pd.Timestamp("2024-01-15")
        df["actual_delivery_date"] = pd.Timestamp("2024-01-10")  # Early delivery
        df["delay_days"] = 5
        stats: dict = {}
        result = pipeline.recalculate_derived_fields(df, stats)
        # Early delivery → delay_days = 0
        assert (result["delay_days"] == 0).all()


# ---------------------------------------------------------------------------
# 7. Categorical normalization
# ---------------------------------------------------------------------------
class TestCategoricalNormalization:

    def test_transport_mode_normalized(self):
        df = make_base_df(4)
        df["transport_mode"] = ["road", "ROAD", " Road ", "Air"]
        stats: dict = {}
        result = pipeline.clean_categorical_values(df, stats)
        assert set(result["transport_mode"]) <= {"Road", "Air"}

    def test_priority_normalized(self):
        df = make_base_df(4)
        df["priority"] = ["low", "HIGH", " Medium ", "critical"]
        stats: dict = {}
        result = pipeline.clean_categorical_values(df, stats)
        assert set(result["priority"]) <= {"Low", "High", "Medium", "Critical"}

    def test_unknown_transport_mode_set_to_unknown(self):
        df = make_base_df(2)
        df["transport_mode"] = ["spacecraft", "teleportation"]
        stats: dict = {}
        result = pipeline.clean_categorical_values(df, stats)
        assert (result["transport_mode"] == "Unknown").all()

    def test_origin_destination_stripped(self):
        df = make_base_df(2)
        df["origin"] = ["  mumbai  ", "delhi"]
        stats: dict = {}
        result = pipeline.clean_categorical_values(df, stats)
        assert result.loc[0, "origin"] == "Mumbai"
        assert result.loc[1, "origin"] == "Delhi"


# ---------------------------------------------------------------------------
# 8. Supplier reference validation
# ---------------------------------------------------------------------------
class TestSupplierReferenceValidation:

    def test_valid_suppliers_kept(self, tmp_path):
        df = make_base_df(3)
        df["supplier_id"] = ["SUP001", "SUP002", "SUP003"]

        suppliers_csv = tmp_path / "suppliers.csv"
        pd.DataFrame({"supplier_id": ["SUP001", "SUP002", "SUP003"]}).to_csv(suppliers_csv, index=False)

        stats: dict = {}
        result = pipeline.validate_references(df, suppliers_csv, tmp_path / "nonexistent.csv", stats)
        assert len(result) == 3
        assert stats["orphan_suppliers"] == 0

    def test_orphan_suppliers_removed(self, tmp_path):
        df = make_base_df(3)
        df["supplier_id"] = ["SUP001", "UNKNOWN_SUP", "SUP003"]

        suppliers_csv = tmp_path / "suppliers.csv"
        pd.DataFrame({"supplier_id": ["SUP001", "SUP003"]}).to_csv(suppliers_csv, index=False)

        products_csv = tmp_path / "products.csv"
        pd.DataFrame({"product_id": df["product_id"].unique()}).to_csv(products_csv, index=False)

        stats: dict = {}
        result = pipeline.validate_references(df, suppliers_csv, products_csv, stats)
        assert len(result) == 2
        assert stats["orphan_suppliers"] == 1

    def test_missing_suppliers_file_skips_validation(self, tmp_path):
        df = make_base_df(3)
        stats: dict = {}
        result = pipeline.validate_references(
            df, tmp_path / "nonexistent.csv", tmp_path / "nonexistent2.csv", stats
        )
        # With no reference file, all rows kept
        assert len(result) == 3


# ---------------------------------------------------------------------------
# 9. Product reference validation
# ---------------------------------------------------------------------------
class TestProductReferenceValidation:

    def test_orphan_products_removed(self, tmp_path):
        df = make_base_df(3)
        df["product_id"] = ["PROD001", "PROD_INVALID", "PROD003"]

        suppliers_csv = tmp_path / "suppliers.csv"
        pd.DataFrame({"supplier_id": df["supplier_id"].unique()}).to_csv(suppliers_csv, index=False)

        products_csv = tmp_path / "products.csv"
        pd.DataFrame({"product_id": ["PROD001", "PROD003"]}).to_csv(products_csv, index=False)

        stats: dict = {}
        result = pipeline.validate_references(df, suppliers_csv, products_csv, stats)
        assert len(result) == 2
        assert stats["orphan_products"] == 1


# ---------------------------------------------------------------------------
# 10. Feature engineering
# ---------------------------------------------------------------------------
class TestFeatureEngineering:

    def setup_method(self):
        """Prepare a clean DataFrame with proper datetime types."""
        df = make_base_df(5)
        df["order_date"] = pd.Timestamp("2024-01-15")          # Monday
        df["expected_delivery_date"] = pd.Timestamp("2024-01-22")
        df["actual_delivery_date"] = pd.Timestamp("2024-01-22")
        df["delay_days"] = 0
        df["inventory_level"] = [500, 300, 600, 100, 700]
        df["demand"] = [400, 400, 400, 400, 400]
        self.df = df

    def test_all_features_created(self):
        stats: dict = {}
        result = pipeline.engineer_features(self.df, stats)
        required_features = [
            "is_delayed", "delivery_status", "inventory_shortage",
            "inventory_coverage_ratio", "total_product_cost", "total_cost",
            "order_year", "order_month", "order_quarter",
            "order_day_of_week", "is_weekend_order", "lead_time_category",
        ]
        for feat in required_features:
            assert feat in result.columns, f"Missing feature: {feat}"

    def test_is_delayed_correct(self):
        df = self.df.copy()
        df["delay_days"] = [0, 3, 0, 5, 0]
        stats: dict = {}
        result = pipeline.engineer_features(df, stats)
        expected = [0, 1, 0, 1, 0]
        assert list(result["is_delayed"]) == expected

    def test_delivery_status_correct(self):
        df = self.df.copy()
        df["delay_days"] = [0, 2, 0, 0, 4]
        stats: dict = {}
        result = pipeline.engineer_features(df, stats)
        assert result.loc[1, "delivery_status"] == "Delayed"
        assert result.loc[0, "delivery_status"] == "On Time"

    def test_inventory_shortage_flag(self):
        df = self.df.copy()
        df["inventory_level"] = [500, 100, 600, 50, 700]
        df["demand"] = [400, 400, 400, 400, 400]
        stats: dict = {}
        result = pipeline.engineer_features(df, stats)
        # Rows 1 and 3 have inventory < demand
        expected = [0, 1, 0, 1, 0]
        assert list(result["inventory_shortage"]) == expected

    def test_total_product_cost(self):
        stats: dict = {}
        result = pipeline.engineer_features(self.df, stats)
        expected = result["quantity"] * result["unit_cost"]
        assert (abs(result["total_product_cost"] - expected) < 0.01).all()

    def test_total_cost(self):
        stats: dict = {}
        result = pipeline.engineer_features(self.df, stats)
        expected = result["total_product_cost"] + result["shipping_cost"]
        assert (abs(result["total_cost"] - expected) < 0.01).all()

    def test_order_date_features(self):
        stats: dict = {}
        result = pipeline.engineer_features(self.df, stats)
        assert (result["order_year"] == 2024).all()
        assert (result["order_month"] == 1).all()
        assert (result["order_quarter"] == 1).all()
        # 2024-01-15 is a Monday → day_of_week=0
        assert (result["order_day_of_week"] == 0).all()
        # Monday is not a weekend
        assert (result["is_weekend_order"] == 0).all()

    def test_weekend_order_flag(self):
        df = self.df.copy()
        # 2024-01-20 is a Saturday
        df["order_date"] = pd.Timestamp("2024-01-20")
        stats: dict = {}
        result = pipeline.engineer_features(df, stats)
        assert (result["is_weekend_order"] == 1).all()

    def test_inventory_coverage_ratio_division_by_zero(self):
        df = self.df.copy()
        df["demand"] = 0
        stats: dict = {}
        result = pipeline.engineer_features(df, stats)
        assert (result["inventory_coverage_ratio"] == np.inf).all()

    def test_lead_time_category_values(self):
        stats: dict = {}
        result = pipeline.engineer_features(self.df, stats)
        assert result["lead_time_category"].isin(["Short", "Medium", "Long", "nan"]).all()


# ---------------------------------------------------------------------------
# 11. Final validation
# ---------------------------------------------------------------------------
class TestFinalValidation:

    def _make_clean_df(self) -> pd.DataFrame:
        df = make_base_df(5)
        # Set proper datetime
        df["order_date"] = pd.Timestamp("2024-01-01")
        df["expected_delivery_date"] = pd.Timestamp("2024-01-08")
        df["actual_delivery_date"] = pd.Timestamp("2024-01-08")
        df["delay_days"] = 0
        df["lead_time"] = 7
        df["lead_time_outlier"] = 0
        # Run feature engineering to get all required columns
        stats: dict = {}
        df = pipeline.engineer_features(df, stats)
        return df

    def test_clean_df_passes_validation(self):
        df = self._make_clean_df()
        results = pipeline.validate_processed_data(df)
        failed = [k for k, v in results.items() if not v]
        assert not failed, f"Validation failed on clean data: {failed}"

    def test_duplicate_id_fails_validation(self):
        df = self._make_clean_df()
        df_dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)
        results = pipeline.validate_processed_data(df_dup)
        assert not results["no_duplicate_shipment_ids"]

    def test_negative_quantity_fails_validation(self):
        df = self._make_clean_df()
        df.loc[0, "quantity"] = -10
        results = pipeline.validate_processed_data(df)
        assert not results["no_negative_quantity"]

    def test_invalid_date_order_fails(self):
        df = self._make_clean_df()
        df.loc[0, "order_date"] = pd.Timestamp("2024-02-01")  # After expected
        df.loc[0, "expected_delivery_date"] = pd.Timestamp("2024-01-01")
        results = pipeline.validate_processed_data(df)
        assert not results["order_date_lte_expected"]
