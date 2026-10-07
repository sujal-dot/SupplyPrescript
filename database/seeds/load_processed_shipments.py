"""Batch loader for Day 2 / Day 3 processed shipments dataset.

Loads data/processed/shipments_processed.csv into PostgreSQL.
- Validates and upserts master data (suppliers and products)
- Performs efficient batch inserts for shipments
- Preserves business shipment IDs
- Avoids duplicate records
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import pandas as pd

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database.connection import SessionLocal, engine
from app.models import Supplier, Product, Shipment
from sqlalchemy import select


def load_processed_shipments(batch_size: int = 1000):
    start_time = time.time()
    csv_path = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "shipments_processed.csv"
    synthetic_suppliers_path = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic" / "suppliers.csv"
    synthetic_products_path = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic" / "products.csv"

    if not csv_path.exists():
        print(f"❌ Processed shipments file not found at: {csv_path}")
        return

    print(f"📦 Loading processed shipments from: {csv_path}")
    df_shipments = pd.read_csv(csv_path)
    total_rows = len(df_shipments)
    print(f"   Read {total_rows:,} records from CSV.")

    session = SessionLocal()
    try:
        # Step 1: Ensure Suppliers master data
        print("🔍 Validating suppliers...")
        existing_supplier_ids = set(session.scalars(select(Supplier.supplier_id)).all())
        
        # Load synthetic suppliers reference if available
        suppliers_to_insert = []
        if synthetic_suppliers_path.exists():
            df_sup = pd.read_csv(synthetic_suppliers_path)
            for _, row in df_sup.iterrows():
                sid = str(row["supplier_id"])
                if sid not in existing_supplier_ids:
                    suppliers_to_insert.append({
                        "supplier_id": sid,
                        "supplier_name": str(row["supplier_name"]),
                        "origin": str(row["origin"]),
                        "supplier_reliability": Decimal(str(round(row["supplier_reliability"], 4))),
                        "base_lead_time": int(row["base_lead_time"]) if pd.notna(row["base_lead_time"]) else None,
                        "capacity": int(row["capacity"]) if pd.notna(row["capacity"]) else None,
                    })
                    existing_supplier_ids.add(sid)

        # Check for any suppliers in shipments that are still missing
        unique_shipment_suppliers = df_shipments["supplier_id"].dropna().unique()
        for sid in unique_shipment_suppliers:
            sid_str = str(sid)
            if sid_str not in existing_supplier_ids:
                # Synthesize fallback supplier record
                sample_row = df_shipments[df_shipments["supplier_id"] == sid].iloc[0]
                suppliers_to_insert.append({
                    "supplier_id": sid_str,
                    "supplier_name": f"Supplier {sid_str}",
                    "origin": str(sample_row.get("origin", "Unknown")),
                    "supplier_reliability": Decimal(str(round(float(sample_row.get("supplier_reliability", 0.90)), 4))),
                    "base_lead_time": int(sample_row.get("lead_time", 5)),
                    "capacity": 20000,
                })
                existing_supplier_ids.add(sid_str)

        if suppliers_to_insert:
            session.bulk_insert_mappings(Supplier, suppliers_to_insert)
            session.commit()
            print(f"   ✓ Inserted {len(suppliers_to_insert)} missing suppliers.")
        else:
            print("   ✓ All suppliers are already present.")

        # Step 2: Ensure Products master data
        print("🔍 Validating products...")
        existing_product_ids = set(session.scalars(select(Product.product_id)).all())
        
        products_to_insert = []
        if synthetic_products_path.exists():
            df_prod = pd.read_csv(synthetic_products_path)
            for _, row in df_prod.iterrows():
                pid = str(row["product_id"])
                if pid not in existing_product_ids:
                    products_to_insert.append({
                        "product_id": pid,
                        "product_name": str(row["product_name"]),
                        "category": str(row["category"]),
                        "unit_cost": Decimal(str(round(row["unit_cost"], 2))),
                        "weight_kg": Decimal(str(round(row["weight_kg"], 2))),
                        "base_demand": Decimal(str(round(row["base_demand"], 2))),
                    })
                    existing_product_ids.add(pid)

        unique_shipment_products = df_shipments["product_id"].dropna().unique()
        for pid in unique_shipment_products:
            pid_str = str(pid)
            if pid_str not in existing_product_ids:
                sample_row = df_shipments[df_shipments["product_id"] == pid].iloc[0]
                products_to_insert.append({
                    "product_id": pid_str,
                    "product_name": f"Product {pid_str}",
                    "category": "General",
                    "unit_cost": Decimal(str(round(float(sample_row.get("unit_cost", 10.0)), 2))),
                    "weight_kg": Decimal("1.0"),
                    "base_demand": Decimal(str(round(float(sample_row.get("demand", 100)), 2))),
                })
                existing_product_ids.add(pid_str)

        if products_to_insert:
            session.bulk_insert_mappings(Product, products_to_insert)
            session.commit()
            print(f"   ✓ Inserted {len(products_to_insert)} missing products.")
        else:
            print("   ✓ All products are already present.")

        # Step 3: Insert Shipments in batches
        print("🚢 Loading shipments in batches...")
        existing_shipment_ids = set(session.scalars(select(Shipment.shipment_id)).all())
        print(f"   Found {len(existing_shipment_ids):,} existing shipments in database.")

        records_to_insert = []
        skipped_count = 0
        inserted_count = 0

        for _, row in df_shipments.iterrows():
            ship_id = str(row["shipment_id"])
            if ship_id in existing_shipment_ids:
                skipped_count += 1
                continue

            order_d = datetime.strptime(str(row["order_date"]), "%Y-%m-%d").date()
            exp_d = datetime.strptime(str(row["expected_delivery_date"]), "%Y-%m-%d").date()
            act_d = datetime.strptime(str(row["actual_delivery_date"]), "%Y-%m-%d").date()

            # Date sanity check
            if order_d > exp_d:
                exp_d = order_d
            if order_d > act_d:
                act_d = order_d

            rec = {
                "shipment_id": ship_id,
                "supplier_id": str(row["supplier_id"]),
                "product_id": str(row["product_id"]),
                "origin": str(row["origin"]),
                "destination": str(row["destination"]),
                "order_date": order_d,
                "expected_delivery_date": exp_d,
                "actual_delivery_date": act_d,
                "lead_time": max(1, int(row["lead_time"])),
                "quantity": max(1, int(row["quantity"])),
                "unit_cost": Decimal(str(round(max(0.01, float(row["unit_cost"])), 2))),
                "shipping_cost": Decimal(str(round(max(0.0, float(row["shipping_cost"])), 2))),
                "supplier_reliability": Decimal(str(round(min(1.0, max(0.0, float(row["supplier_reliability"]))), 4))),
                "inventory_level": max(0, int(row["inventory_level"])),
                "demand": max(0, int(row["demand"])),
                "priority": str(row["priority"]),
                "transport_mode": str(row["transport_mode"]),
                "delay_days": max(0, int(row["delay_days"])),
            }
            records_to_insert.append(rec)
            existing_shipment_ids.add(ship_id)

            if len(records_to_insert) >= batch_size:
                session.bulk_insert_mappings(Shipment, records_to_insert)
                session.commit()
                inserted_count += len(records_to_insert)
                records_to_insert = []
                print(f"   ... inserted {inserted_count:,} shipments")

        if records_to_insert:
            session.bulk_insert_mappings(Shipment, records_to_insert)
            session.commit()
            inserted_count += len(records_to_insert)

        elapsed = time.time() - start_time
        print(f"✅ Shipments import finished in {elapsed:.2f}s:")
        print(f"   • Total inserted: {inserted_count:,}")
        print(f"   • Duplicates skipped: {skipped_count:,}")

    except Exception as e:
        session.rollback()
        print(f"❌ Error loading processed shipments: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    load_processed_shipments()
