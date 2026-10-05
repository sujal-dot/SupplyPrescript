"""
SupplyPrescript - Synthetic Supply Chain Data Validator
Validates dataset integrity, schema conformity, business logic constraints, and scenario relationships.
"""

import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
SUPPLIERS_CSV = SCRIPT_DIR / "suppliers.csv"
PRODUCTS_CSV = SCRIPT_DIR / "products.csv"
SHIPMENTS_CSV = SCRIPT_DIR / "shipments.csv"

REQUIRED_SHIPMENT_FIELDS = [
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

REQUIRED_SUPPLIER_FIELDS = [
    "supplier_id",
    "supplier_name",
    "origin",
    "supplier_reliability",
    "base_lead_time",
    "capacity",
]

REQUIRED_PRODUCT_FIELDS = [
    "product_id",
    "product_name",
    "category",
    "unit_cost",
    "weight_kg",
    "base_demand",
]


def validate_dataset() -> bool:
    """Run comprehensive automated validation checks on the generated supply chain datasets."""
    # Check file existence
    for path, name in [(SUPPLIERS_CSV, "suppliers.csv"), (PRODUCTS_CSV, "products.csv"), (SHIPMENTS_CSV, "shipments.csv")]:
        if not path.exists():
            print(f"ERROR: Missing file: {name}")
            return False

    suppliers = pd.read_csv(SUPPLIERS_CSV)
    products = pd.read_csv(PRODUCTS_CSV)
    shipments = pd.read_csv(SHIPMENTS_CSV)

    errors = []

    # 1. Field presence checks
    for field in REQUIRED_SHIPMENT_FIELDS:
        if field not in shipments.columns:
            errors.append(f"Missing required shipment field: {field}")

    for field in REQUIRED_SUPPLIER_FIELDS:
        if field not in suppliers.columns:
            errors.append(f"Missing required supplier field: {field}")

    for field in REQUIRED_PRODUCT_FIELDS:
        if field not in products.columns:
            errors.append(f"Missing required product field: {field}")

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return False

    # 2. Counts
    num_shipments = len(shipments)
    num_suppliers = len(suppliers)
    num_products = len(products)

    if num_shipments < 10000:
        errors.append(f"Shipments count ({num_shipments}) is below minimum requirement of 10,000")
    if num_suppliers < 50:
        errors.append(f"Suppliers count ({num_suppliers}) is below requirement of 50")
    if num_products < 100:
        errors.append(f"Products count ({num_products}) is below requirement of 100")

    # 3. Duplicate IDs
    dup_shipments = shipments["shipment_id"].duplicated().sum()
    dup_suppliers = suppliers["supplier_id"].duplicated().sum()
    dup_products = products["product_id"].duplicated().sum()

    if dup_shipments > 0:
        errors.append(f"Duplicate shipment IDs found: {dup_shipments}")
    if dup_suppliers > 0:
        errors.append(f"Duplicate supplier IDs found: {dup_suppliers}")
    if dup_products > 0:
        errors.append(f"Duplicate product IDs found: {dup_products}")

    # 4. Missing values
    missing_shipments = shipments[REQUIRED_SHIPMENT_FIELDS].isnull().sum().sum()
    missing_suppliers = suppliers[REQUIRED_SUPPLIER_FIELDS].isnull().sum().sum()
    missing_products = products[REQUIRED_PRODUCT_FIELDS].isnull().sum().sum()
    total_missing = missing_shipments + missing_suppliers + missing_products

    if total_missing > 0:
        errors.append(f"Total missing/null values: {total_missing}")

    # 5. Foreign Keys
    valid_sup_ids = set(suppliers["supplier_id"])
    valid_prod_ids = set(products["product_id"])

    invalid_sup_refs = (~shipments["supplier_id"].isin(valid_sup_ids)).sum()
    invalid_prod_refs = (~shipments["product_id"].isin(valid_prod_ids)).sum()

    if invalid_sup_refs > 0:
        errors.append(f"Invalid supplier references in shipments: {invalid_sup_refs}")
    if invalid_prod_refs > 0:
        errors.append(f"Invalid product references in shipments: {invalid_prod_refs}")

    # 6. Dates and Lead Time / Delay Days
    order_dt = pd.to_datetime(shipments["order_date"])
    exp_dt = pd.to_datetime(shipments["expected_delivery_date"])
    act_dt = pd.to_datetime(shipments["actual_delivery_date"])

    invalid_order_exp = (order_dt > exp_dt).sum()
    invalid_order_act = (order_dt > act_dt).sum()
    invalid_exp_act = (exp_dt > act_dt).sum()
    invalid_dates_count = invalid_order_exp + invalid_order_act + invalid_exp_act

    if invalid_dates_count > 0:
        errors.append(f"Invalid date sequences (order > exp or exp > act): {invalid_dates_count}")

    # Lead time check
    actual_lead_time_days = (act_dt - order_dt).dt.days
    invalid_lead_time = (shipments["lead_time"] != actual_lead_time_days).sum()
    if invalid_lead_time > 0:
        errors.append(f"Invalid lead_time calculations: {invalid_lead_time}")

    # Delay days check
    actual_delay_days = (act_dt - exp_dt).dt.days
    invalid_delay_days = (shipments["delay_days"] != actual_delay_days).sum()
    negative_delay = (shipments["delay_days"] < 0).sum()
    if invalid_delay_days > 0 or negative_delay > 0:
        errors.append(f"Invalid delay_days calculations: {invalid_delay_days + negative_delay}")

    # 7. Numerical Validity
    invalid_quantities = (shipments["quantity"] <= 0).sum()
    invalid_unit_costs = (shipments["unit_cost"] <= 0).sum()
    invalid_shipping_costs = (shipments["shipping_cost"] <= 0).sum()
    invalid_costs = invalid_unit_costs + invalid_shipping_costs
    invalid_reliability = ((shipments["supplier_reliability"] < 0.70) | (shipments["supplier_reliability"] > 0.99)).sum()
    invalid_inventory = (shipments["inventory_level"] < 0).sum()
    invalid_demand = (shipments["demand"] <= 0).sum()

    if invalid_quantities > 0:
        errors.append(f"Invalid quantities (<= 0): {invalid_quantities}")
    if invalid_costs > 0:
        errors.append(f"Invalid costs (<= 0): {invalid_costs}")
    if invalid_reliability > 0:
        errors.append(f"Invalid supplier reliability (outside [0.70, 0.99]): {invalid_reliability}")
    if invalid_inventory > 0:
        errors.append(f"Invalid inventory level (< 0): {invalid_inventory}")
    if invalid_demand > 0:
        errors.append(f"Invalid demand (<= 0): {invalid_demand}")

    # 8. Scenario Rates
    delayed_pct = (shipments["delay_days"] > 0).mean() * 100
    shortage_pct = (shipments["inventory_level"] < shipments["demand"]).mean() * 100

    if delayed_pct < 15.0 or delayed_pct > 30.0:
        errors.append(f"Delayed shipments percentage {delayed_pct:.2f}% is outside target range 15%-30%")
    if shortage_pct < 5.0 or shortage_pct > 15.0:
        errors.append(f"Inventory shortage percentage {shortage_pct:.2f}% is outside target range 5%-15%")

    # 9. Scenario Verifications
    # Normal shipments exist:
    normal_shipments = shipments[(shipments["delay_days"] == 0) & (shipments["inventory_level"] >= shipments["demand"])]
    if len(normal_shipments) == 0:
        errors.append("No normal shipments found")

    # Supplier reliability correlation check:
    low_rel_delay_rate = (shipments[shipments["supplier_reliability"] < 0.83]["delay_days"] > 0).mean()
    high_rel_delay_rate = (shipments[shipments["supplier_reliability"] >= 0.92]["delay_days"] > 0).mean()
    if low_rel_delay_rate <= high_rel_delay_rate:
        errors.append("Low reliability suppliers do not exhibit higher delay rates than high reliability suppliers")

    # Shortage to priority correlation check:
    shortage_critical_rate = (shipments[shipments["inventory_level"] < shipments["demand"]]["priority"] == "Critical").mean()
    normal_critical_rate = (shipments[shipments["inventory_level"] >= shipments["demand"]]["priority"] == "Critical").mean()
    if shortage_critical_rate <= normal_critical_rate:
        errors.append("Shortage situations do not show elevated Critical priority rates")

    # Transport mode variation in shipping cost check:
    avg_air_cost = shipments[shipments["transport_mode"] == "Air"]["shipping_cost"].mean()
    avg_sea_cost = shipments[shipments["transport_mode"] == "Sea"]["shipping_cost"].mean()
    if avg_air_cost <= avg_sea_cost:
        errors.append("Air freight shipping cost is not higher than Sea freight")

    # Print Validation Report
    print("========================================")
    print("SupplyPrescript Dataset Validation")
    print("========================================")
    print(f"Shipments: {num_shipments:,}")
    print(f"Suppliers: {num_suppliers}")
    print(f"Products: {num_products}\n")

    print(f"Duplicate shipment IDs: {dup_shipments}")
    print(f"Missing values: {total_missing}")
    print(f"Invalid dates: {invalid_dates_count}")
    print(f"Invalid quantities: {invalid_quantities}")
    print(f"Invalid costs: {invalid_costs}")
    print(f"Invalid supplier IDs: {invalid_sup_refs}")
    print(f"Invalid product IDs: {invalid_prod_refs}\n")

    print(f"Delayed shipments: {delayed_pct:.2f}%")
    print(f"Inventory shortage: {shortage_pct:.2f}%\n")

    if not errors:
        print("Dataset validation: PASS")
        print("========================================")
        return True
    else:
        print("Dataset validation: FAIL")
        print("========================================")
        print("Validation Failures:")
        for err in errors:
            print(f" - {err}")
        return False


def main():
    success = validate_dataset()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
