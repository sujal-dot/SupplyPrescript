"""
SupplyPrescript — Automated Tests for Decision Execution API (Day 17)
=====================================================================
Tests for POST /api/decisions and GET /api/decisions:
- End-to-end decision authorization and recording
- Safety gates and Day 15 hard constraint enforcement
- Rejection of infeasible and over-budget options
- Client-supplied value tampering rejection (authoritative server calculation)
- Idempotency with exact matching replay vs 409 conflict handling
- Decision execution history retrieval
"""

import uuid
from decimal import Decimal
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import SessionLocal
from app.models.decision import Decision
from app.models.shipment import Shipment


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_execute_decision_success(client, db_session):
    """1. Valid feasible recommendation can be authorized and recorded."""
    # SHIP000005: Road transit, lead time 13d, delay 3d -> Option A (Air Freight) is feasible
    idemp_key = f"TEST-IDEMP-{uuid.uuid4().hex}"
    payload = {
        "shipment_id": "SHIP000005",
        "option_id": "A",
        "strategy": "AIR_FREIGHT",
        "optimization_run_id": "OPT-TEST-RUN-001",
        "idempotency_key": idemp_key,
        "notes": "Authorized expedited freight for assembly deadline.",
        "approved_by": "Senior Operations Director",
    }

    response = client.post("/api/decisions", json=payload)
    assert response.status_code in (200, 201), response.text
    data = response.json()

    assert data["decision_id"].startswith("DEC-EXEC-")
    assert data["shipment_id"] == "SHIP000005"
    assert data["option_id"] == "A"
    assert data["strategy"] == "AIR_FREIGHT"
    assert data["status"] == "RECORDED"
    assert data["external_action_status"] == "NOT_EXECUTED"
    assert data["estimated_total_cost"] > 0
    assert data["estimated_delivery_days"] > 0
    assert data["constraint_validation"]["budget"] == "PASS"
    assert data["constraint_validation"]["delivery"] == "PASS"
    assert "Decision recorded successfully" in data["message"]

    # Verify persisted record in PostgreSQL
    persisted = db_session.query(Decision).filter(Decision.idempotency_key == idemp_key).first()
    assert persisted is not None
    assert persisted.status == "RECORDED"
    assert persisted.shipment_id == "SHIP000005"
    assert persisted.option_id == "A"
    assert persisted.external_action_status == "NOT_EXECUTED"


def test_execute_decision_nonexistent_shipment_rejected(client):
    """2. Nonexistent shipment is rejected with 404."""
    payload = {
        "shipment_id": "NON_EXISTENT_SHIPMENT_99999",
        "option_id": "A",
        "strategy": "AIR_FREIGHT",
    }
    response = client.post("/api/decisions", json=payload)
    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]


def test_execute_decision_invalid_option_rejected(client):
    """3. Unknown / unsupported option identifier is rejected with 404."""
    payload = {
        "shipment_id": "SHIP000005",
        "option_id": "Z",  # Invalid option
    }
    response = client.post("/api/decisions", json=payload)
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_execute_decision_strategy_mismatch_rejected(client):
    """4. Option belonging to different strategy is rejected with 400."""
    payload = {
        "shipment_id": "SHIP000005",
        "option_id": "A",  # Option A is AIR_FREIGHT
        "strategy": "SECONDARY_SUPPLIER",  # Mismatch
    }
    response = client.post("/api/decisions", json=payload)
    assert response.status_code == 400
    assert "Strategy mismatch" in response.json()["detail"]


def test_execute_decision_infeasible_option_rejected(client):
    """5. Infeasible / unconfigured options cannot be recorded as executable."""
    # Option C in baseline has unconfigured financial impact for launch delay (INSUFFICIENT_DATA)
    payload = {
        "shipment_id": "SHIP000005",
        "option_id": "C",
        "strategy": "DELAY_LAUNCH",
    }
    response = client.post("/api/decisions", json=payload)
    assert response.status_code == 400
    assert "violates hard business constraints" in response.json()["detail"] or "Cannot execute" in response.json()["detail"]


def test_execute_decision_over_budget_rejected(client):
    """6. An option violating the hard budget ceiling is rejected."""
    # Mock evaluate_alternatives to return an over-budget Option A
    from optimization.decision_schemas import AlternativeOption, FeasibilityStatus

    fake_option_a = AlternativeOption(
        option_id="A",
        name="Air Freight",
        strategy="AIR_FREIGHT",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=85000.0,  # Exceeds $50,000 budget ceiling
        estimated_delivery_days=2.5,
        delay_probability=0.1,
    )

    with patch("app.api.routes.decisions.evaluate_alternatives") as mock_eval:
        mock_eval.return_value = ([fake_option_a], {})
        payload = {
            "shipment_id": "SHIP000005",
            "option_id": "A",
            "strategy": "AIR_FREIGHT",
        }
        response = client.post("/api/decisions", json=payload)
        assert response.status_code == 400
        assert "budget" in response.json()["detail"].lower()


def test_execute_decision_client_costs_ignored(client):
    """9. Client-supplied costs or estimates cannot override server-side calculations."""
    payload = {
        "shipment_id": "SHIP000005",
        "option_id": "A",
        "strategy": "AIR_FREIGHT",
        # Malicious client attempts to claim total cost is $1.00
        "estimated_total_cost": 1.00,
        "estimated_delivery_days": 0.01,
    }
    response = client.post("/api/decisions", json=payload)
    assert response.status_code in (200, 201)
    data = response.json()
    # Authoritative calculation for SHIP000005 Air Freight is ~$41k, definitely not $1.00!
    assert data["estimated_total_cost"] > 1000.0
    assert data["estimated_delivery_days"] > 1.0


def test_execute_decision_idempotent_replay(client, db_session):
    """10. Repeated requests with same idempotency key return existing record without duplicates."""
    idemp_key = f"IDEMP-REPLAY-{uuid.uuid4().hex}"
    payload = {
        "shipment_id": "SHIP000005",
        "option_id": "A",
        "strategy": "AIR_FREIGHT",
        "idempotency_key": idemp_key,
        "notes": "Test idempotent replay",
    }

    # First execution (new decision -> 201 Created)
    res1 = client.post("/api/decisions", json=payload)
    assert res1.status_code == 201
    data1 = res1.json()

    # Second execution (identical payload & key -> 200 OK replay)
    res2 = client.post("/api/decisions", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()

    # Must return exact same decision ID
    assert data1["decision_id"] == data2["decision_id"]
    assert "idempotent" in data2["message"].lower()

    # Exactly 1 record should exist in database for this key
    count = db_session.query(Decision).filter(Decision.idempotency_key == idemp_key).count()
    assert count == 1


def test_execute_decision_idempotency_conflict_rejected(client):
    """11. Reusing an idempotency key with conflicting decision parameters is rejected (409 Conflict)."""
    idemp_key = f"IDEMP-CONFLICT-{uuid.uuid4().hex}"

    # First request: SHIP000005 Option A
    payload1 = {
        "shipment_id": "SHIP000005",
        "option_id": "A",
        "strategy": "AIR_FREIGHT",
        "idempotency_key": idemp_key,
    }
    res1 = client.post("/api/decisions", json=payload1)
    assert res1.status_code in (200, 201)

    # Second request: Reusing SAME key for Option B
    payload2 = {
        "shipment_id": "SHIP000005",
        "option_id": "B",
        "strategy": "SECONDARY_SUPPLIER",
        "idempotency_key": idemp_key,
    }
    res2 = client.post("/api/decisions", json=payload2)
    assert res2.status_code == 409
    assert "Idempotency conflict" in res2.json()["detail"]


def test_execute_decision_database_failure_returns_500(client):
    """12. Database transaction failure produces clean 500 error without corrupt state."""
    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("Database lock failure")):
        payload = {
            "shipment_id": "SHIP000005",
            "option_id": "A",
            "strategy": "AIR_FREIGHT",
        }
        response = client.post("/api/decisions", json=payload)
        assert response.status_code == 500
        assert "Database transaction failed" in response.json()["detail"]


def test_get_decision_history(client):
    """13. GET /api/decisions returns chronological persisted audit records."""
    # Ensure at least 1 decision exists
    client.post(
        "/api/decisions",
        json={
            "shipment_id": "SHIP000005",
            "option_id": "A",
            "strategy": "AIR_FREIGHT",
            "notes": "History audit test",
        },
    )

    response = client.get("/api/decisions?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert "decisions" in data
    assert len(data["items"]) >= 1

    first = data["items"][0]
    assert "decision_id" in first
    assert "shipment_id" in first
    assert "user_id" in first
    assert "recommendation" in first
    assert "predicted_cost" in first
    assert "predicted_delay" in first
    assert "decision_time" in first
    assert "status" in first
    assert first["external_action_status"] == "NOT_EXECUTED"

    # Test filtering by shipment_id
    filtered_res = client.get("/api/decisions?shipment_id=SHIP000005")
    assert filtered_res.status_code == 200
    filtered_data = filtered_res.json()
    for item in filtered_data["items"]:
        assert item["shipment_id"] == "SHIP000005"


def test_create_decision_day18_contract(client, db_session):
    """14. POST /api/decisions returns 201 Created and matches the Day 18 write-back contract."""
    idemp_key = f"TEST-DAY18-{uuid.uuid4().hex}"
    payload = {
        "shipment_id": "SHIP000005",
        "option_id": "A",
        "recommendation": "AIR_FREIGHT",
        "user_id": "usr_ops_lead_42",
        "idempotency_key": idemp_key,
        "notes": "Day 18 contract compliance verification.",
    }

    response = client.post("/api/decisions", json=payload)
    assert response.status_code == 201
    data = response.json()

    # Verify all 8 required Day 18 fields
    assert "decision_id" in data and data["decision_id"].startswith("DEC-EXEC-")
    assert data["shipment_id"] == "SHIP000005"
    assert data["user_id"] == "usr_ops_lead_42"
    assert data["recommendation"] == "AIR_FREIGHT"
    assert isinstance(data["predicted_cost"], str)
    assert float(data["predicted_cost"]) > 0
    assert isinstance(data["predicted_delay"], (int, float))
    assert "decision_time" in data
    assert data["status"] == "RECORDED"

    # Verify persisted row in PostgreSQL operational database
    row = db_session.query(Decision).filter(Decision.idempotency_key == idemp_key).one()
    assert row.user_id == "usr_ops_lead_42"
    assert row.predicted_cost == Decimal(data["predicted_cost"])
    assert row.status == "RECORDED"
    assert row.decision_time is not None


def test_get_decision_by_id_success(client):
    """15. GET /api/decisions/{id} returns the exact persisted decision record from PostgreSQL."""
    # 1. Create a decision
    idemp_key = f"TEST-BYID-{uuid.uuid4().hex}"
    create_res = client.post(
        "/api/decisions",
        json={
            "shipment_id": "SHIP000005",
            "option_id": "A",
            "recommendation": "AIR_FREIGHT",
            "user_id": "usr_lookup_test",
            "idempotency_key": idemp_key,
            "notes": "Lookup by ID verification.",
        },
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    dec_id = created_data["decision_id"]

    # 2. Fetch by ID
    get_res = client.get(f"/api/decisions/{dec_id}")
    assert get_res.status_code == 200
    fetched_data = get_res.json()

    assert fetched_data["decision_id"] == dec_id
    assert fetched_data["shipment_id"] == "SHIP000005"
    assert fetched_data["user_id"] == "usr_lookup_test"
    assert fetched_data["recommendation"] == "AIR_FREIGHT"
    assert fetched_data["predicted_cost"] == created_data["predicted_cost"]
    assert fetched_data["status"] == "RECORDED"
    assert fetched_data["external_action_status"] == "NOT_EXECUTED"


def test_get_decision_by_id_not_found(client):
    """16. GET /api/decisions/{id} returns 404 for nonexistent decision ID."""
    response = client.get("/api/decisions/DEC-NONEXISTENT-99999999")
    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]


def test_list_decisions_pagination_and_filters(client):
    """17. GET /api/decisions supports limit, offset, and user_id/status filters."""
    # Query with custom limit and offset
    response = client.get("/api/decisions?limit=5&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 5
    assert data["offset"] == 0
    assert "items" in data
    assert len(data["items"]) <= 5

    # Query with status filter
    res_status = client.get("/api/decisions?status=RECORDED&limit=5")
    assert res_status.status_code == 200
    for item in res_status.json()["items"]:
        assert item["status"] == "RECORDED"

    # Query with unmatched filter returns empty collection
    res_empty = client.get("/api/decisions?shipment_id=NON_EXISTENT_QUERY_9999")
    assert res_empty.status_code == 200
    assert res_empty.json()["total"] == 0
    assert len(res_empty.json()["items"]) == 0


def test_create_decision_invalid_payload_rejected(client):
    """18. POST /api/decisions rejects invalid payloads missing required shipment_id or option_id."""
    # Missing option_id
    res1 = client.post("/api/decisions", json={"shipment_id": "SHIP000005"})
    assert res1.status_code == 422

    # Missing shipment_id
    res2 = client.post("/api/decisions", json={"option_id": "A"})
    assert res2.status_code == 422


def test_write_back_end_to_end_lifecycle(client, db_session):
    """19. End-to-end write-back lifecycle: create -> verify in DB -> list -> retrieve by ID."""
    idemp_key = f"TEST-E2E-{uuid.uuid4().hex}"
    create_payload = {
        "shipment_id": "SHIP000005",
        "option_id": "A",
        "recommendation": "AIR_FREIGHT",
        "user_id": "usr_e2e_lead",
        "idempotency_key": idemp_key,
        "notes": "Full end-to-end integration test.",
        "approved_by": "E2E Lead Auditor",
    }

    # 1. POST /api/decisions -> 201 Created
    create_res = client.post("/api/decisions", json=create_payload)
    assert create_res.status_code == 201
    created = create_res.json()
    dec_id = created["decision_id"]

    # 2. Verify raw row in PostgreSQL
    db_row = db_session.query(Decision).filter(Decision.decision_id == dec_id).one()
    assert db_row.shipment_id == "SHIP000005"
    assert db_row.user_id == "usr_e2e_lead"
    assert db_row.strategy == "AIR_FREIGHT"
    assert db_row.status == "RECORDED"
    assert db_row.external_action_status == "NOT_EXECUTED"
    assert db_row.predicted_cost > 0
    assert db_row.decision_time is not None

    # 3. GET /api/decisions?shipment_id=SHIP000005
    list_res = client.get("/api/decisions?shipment_id=SHIP000005&limit=20")
    assert list_res.status_code == 200
    matching = [it for it in list_res.json()["items"] if it["decision_id"] == dec_id]
    assert len(matching) == 1
    assert matching[0]["user_id"] == "usr_e2e_lead"

    # 4. GET /api/decisions/{id}
    detail_res = client.get(f"/api/decisions/{dec_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["decision_id"] == dec_id
    assert detail["predicted_cost"] == created["predicted_cost"]
    assert detail["predicted_delay"] == created["predicted_delay"]


def test_existing_optimization_api_remains_functional(client):
    """20. Existing POST /api/optimize continues to operate normally."""
    response = client.post("/api/optimize", json={"shipment_id": "SHIP000005"})
    assert response.status_code == 200
    data = response.json()
    assert data["shipment_id"] == "SHIP000005"
    assert len(data["options"]) >= 3
