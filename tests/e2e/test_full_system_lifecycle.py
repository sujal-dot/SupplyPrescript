"""
SupplyPrescript — Full End-to-End System Lifecycle Test (Day 24)
================================================================
Comprehensive end-to-end verification across the complete SupplyPrescript operational loop:
1. Authentication & JWT Token Acquisition.
2. Shipment Data Loading & Verification.
3. ML Delay Risk & Duration Prediction (POST /api/predict).
4. PuLP Decision Alternatives Generation & Feasibility Auditing.
5. Day 15 Safety Gate Hard Constraint Enforcement.
6. Infeasible Execution Rejection (assert 400).
7. Decision Authorization & PostgreSQL Persistence (POST /api/decisions).
8. Idempotency Verification (200 Replay vs 409 Conflict).
9. Persisted Decision Retrieval (GET /api/decisions/{id}).
10. Operational Actual Outcome Recording (POST /api/decisions/{id}/outcome).
11. Closed-Loop Prediction-vs-Actual Comparison & Variance Analysis.
12. Decision ROI Engine & Verified Financial Savings Calculation (GET /api/decisions/{id}/roi).
13. Model Feedback Pipeline & Verified Dataset Snapshot (POST /api/feedback/generate).
14. Model Feedback Accuracy Evaluation (POST /api/feedback/evaluate).
15. Drift & Degradation Monitoring (GET /api/ml/retraining/monitor).
16. Monitored Retraining Execution (POST /api/ml/retraining/run).
17. Candidate Model Evaluation & Safe Promotion / Rollback Verification.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.database.connection import SessionLocal
from app.main import app
from app.models.decision import Decision
from app.models.outcome import Outcome
from app.models.feedback import Feedback


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_full_operational_and_learning_lifecycle(client, db_session):
    # -------------------------------------------------------------------------
    # Step 1: Authentication & JWT Token Acquisition
    # -------------------------------------------------------------------------
    op_login = client.post(
        "/api/auth/token",
        json={"username": "operator", "password": "Operator123!"},
    )
    assert op_login.status_code == 200, "Operator login failed"
    op_token = op_login.json()["access_token"]
    op_headers = {"Authorization": f"Bearer {op_token}"}

    admin_login = client.post(
        "/api/auth/token",
        json={"username": "admin", "password": "Admin123!"},
    )
    assert admin_login.status_code == 200, "Admin login failed"
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # -------------------------------------------------------------------------
    # Step 2: Shipment Data Loading
    # -------------------------------------------------------------------------
    shipment_resp = client.get("/api/shipments?page_size=10", headers=op_headers)
    assert shipment_resp.status_code == 200
    shipments_data = shipment_resp.json()
    shipments_list = shipments_data.get("data", [])
    assert len(shipments_list) >= 1
    # Pick a valid test shipment
    shipment_data = next((s for s in shipments_list if s["shipment_id"] == "SHIP000005"), shipments_list[0])
    target_shipment_id = shipment_data["shipment_id"]
    supplier_id = shipment_data["supplier_id"]

    # -------------------------------------------------------------------------
    # Step 3: ML Delay Risk & Duration Prediction
    # -------------------------------------------------------------------------
    predict_payload = {
        "supplier_id": 1,
        "product_id": 1,
        "quantity": 500,
        "inventory_level": 1200,
        "transport_mode": "Air",
    }
    pred_resp = client.post("/api/predict", json=predict_payload, headers=op_headers)
    assert pred_resp.status_code == 200
    pred_data = pred_resp.json()
    assert "delay_probability" in pred_data
    assert "predicted_delay_days" in pred_data
    assert "risk" in pred_data
    assert pred_data["model_version"] == "v1.0"

    # -------------------------------------------------------------------------
    # Step 4: PuLP Decision Alternatives Generation & Auditing
    # -------------------------------------------------------------------------
    alt_resp = client.get(f"/api/optimization/alternatives/{target_shipment_id}", headers=op_headers)
    assert alt_resp.status_code == 200
    alt_data = alt_resp.json()
    assert "alternatives" in alt_data
    alternatives = alt_data["alternatives"]
    assert len(alternatives) >= 1

    option_a = next((opt for opt in alternatives if opt["option_id"] == "A"), alternatives[0])
    assert option_a is not None, "Alternative option must exist"
    assert option_a["feasibility"] == "FEASIBLE"

    # -------------------------------------------------------------------------
    # Step 5 & 6: Safety Gate Violation Rejection (Infeasible execution rejected)
    # -------------------------------------------------------------------------
    # Attempt to execute an unknown or infeasible option -> 400 or 404
    bad_exec = client.post(
        "/api/decisions",
        headers=op_headers,
        json={
            "shipment_id": target_shipment_id,
            "option_id": "Z",
            "recommendation": "AIR_FREIGHT",
            "idempotency_key": f"TEST-FAIL-{uuid.uuid4().hex}",
        },
    )
    assert bad_exec.status_code in [400, 404]

    # -------------------------------------------------------------------------
    # Step 7: Authorized Decision Execution & Persistence (Day 18 Write-Back)
    # -------------------------------------------------------------------------
    idemp_key = f"TEST-LIFECYCLE-{uuid.uuid4().hex[:12]}"
    exec_payload = {
        "shipment_id": target_shipment_id,
        "option_id": option_a["option_id"],
        "recommendation": option_a.get("strategy", "AIR_FREIGHT"),
        "idempotency_key": idemp_key,
        "notes": "Day 24 full lifecycle automated execution test.",
    }
    exec_resp = client.post("/api/decisions", headers=op_headers, json=exec_payload)
    assert exec_resp.status_code == 201
    exec_data = exec_resp.json()
    dec_id = exec_data["decision_id"]
    assert dec_id.startswith("DEC-EXEC-")
    assert exec_data["status"] == "RECORDED"
    assert exec_data["idempotency_key"] == idemp_key

    # -------------------------------------------------------------------------
    # Step 8: Idempotency Replay (200) vs Conflict (409)
    # -------------------------------------------------------------------------
    # Exact replay returns 200 OK
    replay_resp = client.post("/api/decisions", headers=op_headers, json=exec_payload)
    assert replay_resp.status_code == 200
    assert replay_resp.json()["decision_id"] == dec_id

    # Reusing idempotency key with conflicting option returns 409 Conflict
    conflict_payload = exec_payload.copy()
    conflict_payload["option_id"] = "B"
    conflict_payload["recommendation"] = "SECONDARY_SUPPLIER"
    conflict_resp = client.post("/api/decisions", headers=op_headers, json=conflict_payload)
    assert conflict_resp.status_code == 409

    # -------------------------------------------------------------------------
    # Step 9: Persisted Decision Retrieval
    # -------------------------------------------------------------------------
    get_dec_resp = client.get(f"/api/decisions/{dec_id}", headers=op_headers)
    assert get_dec_resp.status_code == 200
    assert get_dec_resp.json()["decision_id"] == dec_id

    # -------------------------------------------------------------------------
    # Step 10: Operational Actual Outcome Recording (Day 19 Closed-Loop)
    # -------------------------------------------------------------------------
    outcome_payload = {
        "actual_cost": 4250.00,
        "actual_delivery_date": "2026-10-25",
        "actual_delay_days": 1.0,
        "delivery_status": "DELIVERED_ON_TIME",
        "notes": "Expedited transit arrived on time with minimal delay.",
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

    # -------------------------------------------------------------------------
    # Step 11: Outcome Variance & Comparison Verification
    # -------------------------------------------------------------------------
    assert "cost_variance" in outcome_data["variance"]
    assert "delay_variance" in outcome_data["variance"]
    assert outcome_data["data_completeness"] in ["COMPLETE", "PARTIAL"]

    # -------------------------------------------------------------------------
    # Step 12: Decision ROI Engine & Verified Savings (Day 20 Analytics)
    # -------------------------------------------------------------------------
    roi_resp = client.get(f"/api/decisions/{dec_id}/roi", headers=op_headers)
    assert roi_resp.status_code == 200
    roi_data = roi_resp.json()
    assert roi_data["decision_id"] == dec_id
    assert "cost" in roi_data
    assert "cost_difference" in roi_data["cost"]
    assert "decision_evaluation" in roi_data
    assert "decision_success" in roi_data["decision_evaluation"]
    assert "roi" in roi_data

    # -------------------------------------------------------------------------
    # Step 13: Model Feedback Pipeline & Dataset Snapshot (Day 22)
    # -------------------------------------------------------------------------
    fb_resp = client.post(
        "/api/feedback/generate",
        headers=admin_headers,
        json={"export_dataset": True, "force_refresh": True},
    )
    assert fb_resp.status_code == 200
    fb_data = fb_resp.json()
    assert fb_data["processed_count"] >= 1
    assert fb_data["dataset_version"] is not None

    # -------------------------------------------------------------------------
    # Step 14: Model Feedback Accuracy Evaluation
    # -------------------------------------------------------------------------
    eval_resp = client.post(
        "/api/feedback/evaluate",
        headers=admin_headers,
        json={"model_version": "v1.0", "min_sample_threshold": 1},
    )
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["model_version"] == "v1.0"
    assert eval_data["status"] in ["EVALUATED", "INSUFFICIENT_DATA"]

    # -------------------------------------------------------------------------
    # Step 15: Drift & Degradation Monitoring (Day 23)
    # -------------------------------------------------------------------------
    mon_resp = client.get("/api/ml/retraining/monitor", headers=admin_headers)
    assert mon_resp.status_code == 200
    mon_data = mon_resp.json()
    assert "is_degraded" in mon_data
    assert "status" in mon_data

    # -------------------------------------------------------------------------
    # Step 16: Monitored Retraining Execution
    # -------------------------------------------------------------------------
    retrain_resp = client.post(
        "/api/ml/retraining/run",
        headers=admin_headers,
        json={"force": True, "trigger_reason": "Day 24 end-to-end integration test"},
    )
    assert retrain_resp.status_code == 200
    retrain_data = retrain_resp.json()
    assert retrain_data["status"] in ["REGISTERED", "REJECTED", "HEALTHY", "BLOCKED"]

    # -------------------------------------------------------------------------
    # Step 17: Candidate Validation & Safe Rollback Verification
    # -------------------------------------------------------------------------
    # Verify rollback capability to stable v1.0
    rollback_resp = client.post(
        "/api/ml/retraining/rollback",
        headers=admin_headers,
        json={"target_version": "v1.0"},
    )
    assert rollback_resp.status_code == 200
    rollback_data = rollback_resp.json()
    assert rollback_data["status"] in ["SUCCESS", "ROLLED_BACK"]
    assert rollback_data["active_version"] == "v1.0"
