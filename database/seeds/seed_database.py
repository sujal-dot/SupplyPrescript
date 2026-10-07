"""Seed database script for SupplyPrescript.

Inserts a small representative development dataset:
- 10 Suppliers
- 20 Products
- 50 Shipments
- 20 Inventory records
- 2 Model versions
- Sample Predictions, Recommendations, Decisions, Outcomes
Safe to run repeatedly without creating duplicates.
"""

import sys
import os
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database.connection import SessionLocal
from app.models import (
    Supplier,
    Product,
    Shipment,
    Inventory,
    ModelVersion,
    Prediction,
    Recommendation,
    Decision,
    Outcome,
)


def seed_database():
    session = SessionLocal()
    try:
        print("🌱 Seeding database...")

        # 1. Seed 10 Suppliers
        suppliers_data = [
            {"supplier_id": "SUP001", "supplier_name": "Apex Micro Electronics", "origin": "Bengaluru", "supplier_reliability": Decimal("0.9500"), "base_lead_time": 5, "capacity": 23000},
            {"supplier_id": "SUP002", "supplier_name": "Havells Industrial Components", "origin": "Noida", "supplier_reliability": Decimal("0.8000"), "base_lead_time": 3, "capacity": 20000},
            {"supplier_id": "SUP003", "supplier_name": "Siemens Energy Electricals", "origin": "Gurugram", "supplier_reliability": Decimal("0.9500"), "base_lead_time": 2, "capacity": 8000},
            {"supplier_id": "SUP004", "supplier_name": "ABB Power Automation", "origin": "Bengaluru", "supplier_reliability": Decimal("0.9000"), "base_lead_time": 5, "capacity": 34000},
            {"supplier_id": "SUP005", "supplier_name": "Schneider Electric Solutions", "origin": "Chennai", "supplier_reliability": Decimal("0.8500"), "base_lead_time": 4, "capacity": 15000},
            {"supplier_id": "SUP006", "supplier_name": "Tata AutoComp Systems", "origin": "Pune", "supplier_reliability": Decimal("0.9200"), "base_lead_time": 6, "capacity": 28000},
            {"supplier_id": "SUP007", "supplier_name": "Bharat Forge Precision", "origin": "Pune", "supplier_reliability": Decimal("0.8800"), "base_lead_time": 4, "capacity": 22000},
            {"supplier_id": "SUP008", "supplier_name": "Bosch India Mobility", "origin": "Bengaluru", "supplier_reliability": Decimal("0.9600"), "base_lead_time": 3, "capacity": 31000},
            {"supplier_id": "SUP009", "supplier_name": "Larsen & Toubro Electrical", "origin": "Mumbai", "supplier_reliability": Decimal("0.9100"), "base_lead_time": 5, "capacity": 19000},
            {"supplier_id": "SUP010", "supplier_name": "Minda Industries Electronics", "origin": "Manesar", "supplier_reliability": Decimal("0.8400"), "base_lead_time": 3, "capacity": 17000},
        ]

        inserted_suppliers = 0
        for s in suppliers_data:
            existing = session.query(Supplier).filter_by(supplier_id=s["supplier_id"]).first()
            if not existing:
                session.add(Supplier(**s))
                inserted_suppliers += 1
        session.commit()
        print(f"  ✓ Suppliers seeded: {inserted_suppliers} inserted (total {len(suppliers_data)})")

        # 2. Seed 20 Products
        categories = ["Electronics", "Mechanical", "Electrical", "Hydraulics"]
        products_data = []
        for i in range(1, 21):
            prod_id = f"PROD{i:03d}"
            cat = categories[(i - 1) % len(categories)]
            unit_cost = Decimal(f"{15 + (i * 7.5):.2f}")
            weight = Decimal(f"{0.2 + (i * 0.15):.2f}")
            base_dem = Decimal(f"{200 + (i * 25):.2f}")
            products_data.append({
                "product_id": prod_id,
                "product_name": f"{cat} Component SKU-{i:03d}",
                "category": cat,
                "unit_cost": unit_cost,
                "weight_kg": weight,
                "base_demand": base_dem,
            })

        inserted_products = 0
        for p in products_data:
            existing = session.query(Product).filter_by(product_id=p["product_id"]).first()
            if not existing:
                session.add(Product(**p))
                inserted_products += 1
        session.commit()
        print(f"  ✓ Products seeded: {inserted_products} inserted (total {len(products_data)})")

        # 3. Seed 50 Shipments
        destinations = ["Delhi", "Mumbai", "Chennai", "Kolkata", "Hyderabad", "Ahmedabad"]
        modes = ["Road", "Rail", "Air", "Sea"]
        priorities = ["Low", "Medium", "High"]

        inserted_shipments = 0
        base_date = date(2023, 1, 1)

        for i in range(1, 51):
            ship_id = f"SHIP{i:06d}"
            sup_id = f"SUP{((i - 1) % 10) + 1:03d}"
            prod_id = f"PROD{((i - 1) % 20) + 1:03d}"
            lead = 3 + (i % 8)
            delay = (i % 5) if (i % 7 == 0) else 0
            o_date = base_date + timedelta(days=(i * 3))
            exp_date = o_date + timedelta(days=lead)
            act_date = exp_date + timedelta(days=delay)
            qty = 100 + (i * 15)
            u_cost = Decimal(f"{25 + (i % 10) * 5:.2f}")
            s_cost = Decimal(f"{150 + (i * 12.5):.2f}")
            rel = Decimal(f"{0.80 + (i % 20) * 0.01:.4f}")
            inv_lvl = 500 + (i * 20)
            dem = 300 + (i * 15)

            existing = session.query(Shipment).filter_by(shipment_id=ship_id).first()
            if not existing:
                shipment = Shipment(
                    shipment_id=ship_id,
                    supplier_id=sup_id,
                    product_id=prod_id,
                    origin="Bengaluru" if i % 2 == 0 else "Pune",
                    destination=destinations[i % len(destinations)],
                    order_date=o_date,
                    expected_delivery_date=exp_date,
                    actual_delivery_date=act_date,
                    lead_time=lead,
                    quantity=qty,
                    unit_cost=u_cost,
                    shipping_cost=s_cost,
                    supplier_reliability=rel,
                    inventory_level=inv_lvl,
                    demand=dem,
                    priority=priorities[i % len(priorities)],
                    transport_mode=modes[i % len(modes)],
                    delay_days=delay,
                )
                session.add(shipment)
                inserted_shipments += 1
        session.commit()
        print(f"  ✓ Shipments seeded: {inserted_shipments} inserted (total 50)")

        # 4. Seed 20 Inventory Records
        statuses = ["Healthy", "Low", "Critical", "Out of Stock"]
        inserted_inventory = 0
        for i in range(1, 21):
            prod_id = f"PROD{i:03d}"
            inv_date = base_date + timedelta(days=i * 5)
            inv_lvl = 200 + (i * 30)
            dem = 150 + (i * 20)
            reorder = 180 + (i * 15)
            safety = 50 + (i * 5)
            status = statuses[i % len(statuses)]

            existing = session.query(Inventory).filter_by(product_id=prod_id, inventory_date=inv_date).first()
            if not existing:
                inv = Inventory(
                    product_id=prod_id,
                    inventory_date=inv_date,
                    inventory_level=inv_lvl,
                    demand=dem,
                    reorder_point=reorder,
                    safety_stock=safety,
                    inventory_status=status,
                )
                session.add(inv)
                inserted_inventory += 1
        session.commit()
        print(f"  ✓ Inventory seeded: {inserted_inventory} inserted (total 20)")

        # 5. Seed 2 Model Versions
        model_versions_data = [
            {
                "model_name": "delay_risk_classifier",
                "version": "v1.0.0",
                "model_type": "Classification",
                "algorithm": "XGBoost",
                "training_date": datetime(2023, 6, 1, 10, 0, tzinfo=timezone.utc),
                "dataset_version": "v1.0-processed",
                "metrics": {"accuracy": 0.92, "precision": 0.90, "recall": 0.88, "f1": 0.89},
                "model_path": "models/delay_classifier_v1.xgb",
                "is_active": True,
            },
            {
                "model_name": "demand_forecaster",
                "version": "v1.0.0",
                "model_type": "Regression",
                "algorithm": "LightGBM",
                "training_date": datetime(2023, 6, 15, 12, 0, tzinfo=timezone.utc),
                "dataset_version": "v1.0-processed",
                "metrics": {"rmse": 14.2, "mae": 10.5, "r2": 0.94},
                "model_path": "models/demand_forecaster_v1.lgb",
                "is_active": True,
            },
        ]
        inserted_models = 0
        for mv in model_versions_data:
            existing = session.query(ModelVersion).filter_by(
                model_name=mv["model_name"], version=mv["version"]
            ).first()
            if not existing:
                session.add(ModelVersion(**mv))
                inserted_models += 1
        session.commit()
        print(f"  ✓ Model versions seeded: {inserted_models} inserted (total 2)")

        # 6. Seed Complete Core Workflow:
        # Prediction -> Recommendation -> Decision -> Outcome
        # We need model_version id
        model_v1 = session.query(ModelVersion).filter_by(model_name="delay_risk_classifier").first()

        sample_workflow = [
            {
                "pred_id": "PRED000001",
                "ship_id": "SHIP000001",
                "pred_type": "Delay Risk",
                "pred_val": Decimal("1.0000"),
                "pred_prob": Decimal("0.8500"),
                "rec_id": "REC000001",
                "rec_type": "Expedite Shipment",
                "rec_text": "High risk of delivery delay detected for SHIP000001. Recommend expediting via express freight.",
                "rec_action": "Switch to Express Air Freight",
                "confidence": Decimal("0.8750"),
                "dec_id": "DEC000001",
                "decision": "Approved Air Freight Expediting",
                "dec_reason": "Critical component needed for production assembly line.",
                "dec_source": "Human",
                "approved_by": "Supply Chain Director",
                "out_id": "OUT000001",
                "out_status": "Success",
                "act_delay": 0,
                "act_cost": Decimal("250.00"),
                "success_score": Decimal("0.9500"),
                "out_notes": "Delivered on schedule. Production downtime averted.",
            },
            {
                "pred_id": "PRED000002",
                "ship_id": "SHIP000002",
                "pred_type": "Delivery Time",
                "pred_val": Decimal("14.0000"),
                "pred_prob": Decimal("0.7800"),
                "rec_id": "REC000002",
                "rec_type": "Monitor Supplier",
                "rec_text": "Supplier lead time trending higher than seasonal baseline. Continue monitoring.",
                "rec_action": "Enable proactive tracking alerts",
                "confidence": Decimal("0.8200"),
                "dec_id": "DEC000002",
                "decision": "Active Monitoring Enabled",
                "dec_reason": "Standard automated tracking policy.",
                "dec_source": "AI",
                "approved_by": "System Automated",
                "out_id": "OUT000002",
                "out_status": "Success",
                "act_delay": 0,
                "act_cost": Decimal("0.00"),
                "success_score": Decimal("1.0000"),
                "out_notes": "Monitored successfully. Shipment arrived on time.",
            },
        ]

        inserted_chain = 0
        for wf in sample_workflow:
            pred = session.query(Prediction).filter_by(prediction_id=wf["pred_id"]).first()
            if not pred:
                pred = Prediction(
                    prediction_id=wf["pred_id"],
                    shipment_id=wf["ship_id"],
                    model_version_id=model_v1.id,
                    prediction_type=wf["pred_type"],
                    predicted_value=wf["pred_val"],
                    prediction_probability=wf["pred_prob"],
                    prediction_status="Generated",
                )
                session.add(pred)
                session.flush()

            rec = session.query(Recommendation).filter_by(recommendation_id=wf["rec_id"]).first()
            if not rec:
                rec = Recommendation(
                    recommendation_id=wf["rec_id"],
                    prediction_id=pred.id,
                    recommendation_type=wf["rec_type"],
                    recommendation_text=wf["rec_text"],
                    recommended_action=wf["rec_action"],
                    priority="High",
                    confidence_score=wf["confidence"],
                    status="Active",
                )
                session.add(rec)
                session.flush()

            dec = session.query(Decision).filter_by(decision_id=wf["dec_id"]).first()
            if not dec:
                dec = Decision(
                    decision_id=wf["dec_id"],
                    recommendation_id=rec.id,
                    decision=wf["decision"],
                    decision_reason=wf["dec_reason"],
                    decision_source=wf["dec_source"],
                    approved_by=wf["approved_by"],
                    status="Approved",
                )
                session.add(dec)
                session.flush()

            out = session.query(Outcome).filter_by(outcome_id=wf["out_id"]).first()
            if not out:
                out = Outcome(
                    outcome_id=wf["out_id"],
                    decision_id=dec.id,
                    actual_delay_days=wf["act_delay"],
                    actual_cost=wf["act_cost"],
                    outcome_status=wf["out_status"],
                    success_score=wf["success_score"],
                    outcome_notes=wf["out_notes"],
                )
                session.add(out)
                inserted_chain += 1

        session.commit()
        print(f"  ✓ End-to-end workflow seeded: {inserted_chain} complete chains added")
        print("✅ Database seeding complete!")

    except Exception as e:
        session.rollback()
        print(f"❌ Error during seeding: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
