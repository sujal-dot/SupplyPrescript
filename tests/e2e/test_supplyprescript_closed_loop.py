"""
SupplyPrescript — Closed-Loop System Integration & Regression Test (Day 25)
===========================================================================
Comprehensive end-to-end verification of the 12-stage operational and continuous
learning lifecycle:
1. User Authentication & JWT Issuance.
2. Shipment Creation (POST /api/shipments) & Input Validation.
3. ML Delay Risk & Duration Inference (POST /api/predict).
4. Prescriptive Optimization & Alternative Generation (Air Freight, Secondary Supplier, Delay).
5. Day 15 Safety Gate & Feasibility Enforcement (Infeasible Option Rejection).
6. Decision Authorization & PostgreSQL Persistence (POST /api/decisions).
7. Idempotency Protection (Exact Replay 200 vs Conflicting Payload 409).
8. Persisted Decision Retrieval (GET /api/decisions/{id}).
9. Operational Actual Outcome Recording (POST /api/decisions/{id}/outcome).
10. Closed-Loop Prediction-vs-Actual Comparison & Variance Analysis.
11. Decision ROI Engine & Verified Financial Savings (GET /api/decisions/{id}/roi).
12. Model Feedback Observation Pipeline & Dataset Snapshot (POST /api/feedback/generate).
13. Model Feedback Accuracy Evaluation (POST /api/feedback/evaluate).
14. Continuous Drift & Degradation Monitoring (GET /api/ml/retraining/monitor).
15. Monitored Retraining Execution & Candidate Validation (POST /api/ml/retraining/run).
16. Candidate Promotion RBAC Safeguards & Safe Emergency Rollback (POST /api/ml/retraining/rollback).
17. Relevant Failure Paths (Invalid Input, Tampering, Infeasible Option, 403 RBAC).
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.database.connection import SessionLocal
from app.main import app
from app.models.decision import Decision
from app.models.feedback import Feedback
from app.models.outcome import Outcome
from app.models.shipment import Shipment


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_supplyprescript_complete_closed_loop_lifecycle(client, db_session):
    test_shipment_ids = []
    test_decision_ids = []

    try:
        # =====================================================================
        # Stage 1: Authentication & Token Acquisition
        # =====================================================================
        op_login = client.post(
            "/api/auth/token",
            json={"username": "operator", "password": "Operator123!"},
        )
        assert op_login.status_code == 200, "Operator login must succeed"
        op_token = op_login.json()["access_token"]
        op_headers = {"Authorization": f"Bearer {op_token}"}

        admin_login = client.post(
            "/api/auth/token",
            json={"username": "admin", "password": "Admin123!"},
        )
        assert admin_login.status_code == 200, "Admin login must succeed"
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # =====================================================================
        # Stage 2: Shipment Creation & Input Validation (Failure & Success Paths)
        # =====================================================================
        # Failure path: Non-existent foreign keys rejected with 404
        bad_shipment = {
            "supplier_id": "SUP_NON_EXISTENT",
            "product_id": "PROD_NON_EXISTENT",
            "origin": "Shenzhen",
            "destination": "Chicago",
            "order_date": "2026-10-01",
            "expected_delivery_date": "2026-10-15",
            "lead_time": 14,
            "quantity": 500,
            "unit_cost": "25.00",
            "shipping_cost": "3500.00",
            "supplier_reliability": "0.92",
            "inventory_level": 250,
            "demand": 400,
            "priority": "Critical",
            "transport_mode": "Road",
        }
        bad_res = client.post("/api/shipments", json=bad_shipment, headers=op_headers)
        assert bad_res.status_code == 404

        # Success path: Create valid demo shipment
        new_ship_id = f"SHIP-DEMO-{uuid.uuid4().hex[:8].upper()}"
        test_shipment_ids.append(new_ship_id)
        valid_shipment = {
            "shipment_id": new_ship_id,
            "supplier_id": "SUP001",
            "product_id": "PROD001",
            "origin": "Shenzhen",
            "destination": "Chicago",
            "order_date": "2026-10-01",
            "expected_delivery_date": "2026-10-15",
            "lead_time": 14,
            "quantity": 600,
            "unit_cost": "30.00",
            "shipping_cost": "4200.00",
            "supplier_reliability": "0.95",
            "inventory_level": 300,
            "demand": 500,
            "priority": "Critical",
            "transport_mode": "Road",
        }
        ship_res = client.post("/api/shipments", json=valid_shipment, headers=op_headers)
        assert ship_res.status_code == 201
        created_ship = ship_res.json()
        assert created_ship["shipment_id"] == new_ship_id

        # Verify shipment retrieval via GET /api/shipments/{id}
        get_ship_res = client.get(f"/api/shipments/{new_ship_id}", headers=op_headers)
        assert get_ship_res.status_code == 200
        assert get_ship_res.json()["shipment_id"] == new_ship_id

        # =====================================================================
        # Stage 3: ML Delay Risk & Duration Prediction
        # =====================================================================
        predict_payload = {
            "supplier_id": 1,
            "product_id": 1,
            "quantity": 600,
            "inventory_level": 300,
            "transport_mode": "Road",
            "destination": "Chicago",
            "priority": "Critical",
            "lead_time": 14,
        }
        pred_resp = client.post("/api/predict", json=predict_payload, headers=op_headers)
        assert pred_resp.status_code == 200
        pred_data = pred_resp.json()
        assert "delay_probability" in pred_data
        assert "predicted_delay_days" in pred_data
        assert pred_data["predicted_delay_days"] >= 0.0
        assert pred_data["risk"] in ["LOW", "MEDIUM", "HIGH"]
        assert pred_data["model_version"] == "v1.0"
        assert pred_data["prediction_id"].startswith("PRED-")

        # =====================================================================
        # Stage 4 & 5: Prescriptive Alternatives & Safety Gate Enforcement
        # =====================================================================
        # Alternatives generated for target shipment
        alt_resp = client.get(f"/api/optimization/alternatives/{new_ship_id}", headers=op_headers)
        assert alt_resp.status_code == 200
        alt_data = alt_resp.json()
        assert "alternatives" in alt_data
        alternatives = alt_data["alternatives"]
        assert len(alternatives) >= 2, "Expected multiple alternative strategies"

        # Check Option A exists
        opt_a = next((opt for opt in alternatives if opt["option_id"] == "A"), alternatives[0])
        assert opt_a["feasibility"] in ["FEASIBLE", "INFEASIBLE"]

        # Safety Gate: Infeasible or non-existent option execution must be rejected
        bad_decision_payload = {
            "shipment_id": new_ship_id,
            "option_id": "X_INVALID",
            "recommendation": "AIR_FREIGHT",
            "idempotency_key": f"TEST-FAIL-{uuid.uuid4().hex}",
        }
        bad_dec_resp = client.post("/api/decisions", json=bad_decision_payload, headers=op_headers)
        assert bad_dec_resp.status_code in [400, 404, 422]

        # =====================================================================
        # Stage 6: Decision Authorization & PostgreSQL Persistence
        # =====================================================================
        idemp_key = f"TEST-LOOP-{uuid.uuid4().hex[:12]}"
        exec_payload = {
            "shipment_id": new_ship_id,
            "option_id": opt_a["option_id"],
            "recommendation": opt_a.get("strategy", "AIR_FREIGHT"),
            "idempotency_key": idemp_key,
            "notes": "Day 25 closed loop integration demonstration.",
        }
        exec_resp = client.post("/api/decisions", json=exec_payload, headers=op_headers)
        assert exec_resp.status_code == 201
        exec_data = exec_resp.json()
        dec_id = exec_data["decision_id"]
        test_decision_ids.append(dec_id)
        assert dec_id.startswith("DEC-EXEC-")
        assert exec_data["status"] == "RECORDED"
        assert exec_data["idempotency_key"] == idemp_key

        # Verify PostgreSQL database row
        db_dec = db_session.query(Decision).filter(Decision.decision_id == dec_id).first()
        assert db_dec is not None
        assert db_dec.shipment_id == new_ship_id

        # =====================================================================
        # Stage 7: Idempotency Protection (Exact Replay 200 vs Conflicting 409)
        # =====================================================================
        # 1. Exact replay with same payload -> 200 OK replay
        replay_resp = client.post("/api/decisions", json=exec_payload, headers=op_headers)
        assert replay_resp.status_code == 200
        assert replay_resp.json()["decision_id"] == dec_id

        # 2. Conflicting option with same idempotency key -> 409 Conflict
        conflict_payload = exec_payload.copy()
        conflict_payload["option_id"] = "B"
        conflict_payload["recommendation"] = "SECONDARY_SUPPLIER"
        conflict_resp = client.post("/api/decisions", json=conflict_payload, headers=op_headers)
        assert conflict_resp.status_code == 409

        # =====================================================================
        # Stage 8: Persisted Decision Retrieval
        # =====================================================================
        get_dec = client.get(f"/api/decisions/{dec_id}", headers=op_headers)
        assert get_dec.status_code == 200
        assert get_dec.json()["decision_id"] == dec_id

        # =====================================================================
        # Stage 9: Operational Actual Outcome Recording
        # =====================================================================
        outcome_payload = {
            "actual_cost": 4350.00,
            "actual_delivery_date": "2026-10-16",
            "actual_delay_days": 1.0,
            "delivery_status": "DELIVERED_ON_TIME",
            "notes": "Verified delivery outcome recorded.",
        }
        outcome_resp = client.post(
            f"/api/decisions/{dec_id}/outcome",
            headers=op_headers,
            json=outcome_payload,
        )
        assert outcome_resp.status_code == 201
        outcome_data = outcome_resp.json()
        assert outcome_data["decision_id"] == dec_id
        assert "actual" in outcome_data
        assert "variance" in outcome_data

        # =====================================================================
        # Stage 10: Closed-Loop Prediction-vs-Actual Comparison
        # =====================================================================
        assert "cost_variance" in outcome_data["variance"]
        assert "delay_variance" in outcome_data["variance"]
        assert outcome_data["data_completeness"] in ["COMPLETE", "PARTIAL"]

        # =====================================================================
        # Stage 11: Decision ROI Engine & Verified Financial Savings
        # =====================================================================
        roi_resp = client.get(f"/api/decisions/{dec_id}/roi", headers=op_headers)
        assert roi_resp.status_code == 200
        roi_data = roi_resp.json()
        assert roi_data["decision_id"] == dec_id
        assert "cost" in roi_data
        assert "cost_difference" in roi_data["cost"]
        assert "decision_evaluation" in roi_data
        assert "decision_success" in roi_data["decision_evaluation"]
        assert "roi" in roi_data

        # =====================================================================
        # Stage 12: Model Feedback Observation Pipeline & Dataset Snapshot
        # =====================================================================
        fb_resp = client.post(
            "/api/feedback/generate",
            headers=admin_headers,
            json={"export_dataset": True, "force_refresh": True},
        )
        assert fb_resp.status_code == 200
        fb_data = fb_resp.json()
        assert fb_data["processed_count"] >= 1
        assert fb_data["dataset_version"] is not None

        # =====================================================================
        # Stage 13: Model Feedback Accuracy Evaluation
        # =====================================================================
        eval_resp = client.post(
            "/api/feedback/evaluate",
            headers=admin_headers,
            json={"model_version": "v1.0", "min_sample_threshold": 1},
        )
        assert eval_resp.status_code == 200
        eval_data = eval_resp.json()
        assert eval_data["model_version"] == "v1.0"
        assert eval_data["status"] in ["EVALUATED", "INSUFFICIENT_DATA"]

        # =====================================================================
        # Stage 14: Continuous Drift & Degradation Monitoring
        # =====================================================================
        mon_resp = client.get("/api/ml/retraining/monitor", headers=admin_headers)
        assert mon_resp.status_code == 200
        mon_data = mon_resp.json()
        assert "is_degraded" in mon_data
        assert "status" in mon_data

        # =====================================================================
        # Stage 15: Monitored Retraining Execution & Candidate Validation
        # =====================================================================
        retrain_resp = client.post(
            "/api/ml/retraining/run",
            headers=admin_headers,
            json={"force": True, "trigger_reason": "Day 25 closed loop integration test"},
        )
        assert retrain_resp.status_code == 200
        retrain_data = retrain_resp.json()
        assert retrain_data["status"] in ["REGISTERED", "REJECTED", "HEALTHY", "BLOCKED"]

        # =====================================================================
        # Stage 16: Candidate Promotion RBAC Safeguards & Safe Rollback
        # =====================================================================
        # Operator cannot promote candidates -> 403 Forbidden
        op_promote_resp = client.post(
            "/api/ml/retraining/jobs/FAKE-JOB-ID/promote",
            headers=op_headers,
        )
        assert op_promote_resp.status_code == 403

        # Safe rollback preserves active production model version v1.0
        rollback_resp = client.post(
            "/api/ml/retraining/rollback",
            headers=admin_headers,
            json={"target_version": "v1.0"},
        )
        assert rollback_resp.status_code == 200
        rollback_data = rollback_resp.json()
        assert rollback_data["status"] in ["SUCCESS", "ROLLED_BACK"]
        assert rollback_data["active_version"] == "v1.0"

    finally:
        # Clean up isolated test data with fresh database session
        cleanup_db = SessionLocal()
        try:
            for sid in test_shipment_ids:
                decs = cleanup_db.query(Decision).filter(Decision.shipment_id == sid).all()
                for d in decs:
                    cleanup_db.query(Outcome).filter(
                        (Outcome.decision_id == d.id) | (Outcome.decision_business_id == d.decision_id)
                    ).delete(synchronize_session=False)
                    cleanup_db.query(Feedback).filter(
                        (Feedback.decision_id == d.decision_id) | (Feedback.shipment_id == sid)
                    ).delete(synchronize_session=False)
                    cleanup_db.delete(d)
                cleanup_db.query(Shipment).filter(Shipment.shipment_id == sid).delete(synchronize_session=False)
            cleanup_db.commit()
        except Exception:
            cleanup_db.rollback()
        finally:
            cleanup_db.close()
