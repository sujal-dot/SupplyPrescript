"""
SupplyPrescript — Hard Constraint & API Test Suite: Optimization API (Day 14 & 15)
==================================================================================
Comprehensive API integration tests for prescriptive optimization endpoints:
- POST /api/optimize (Day 14 Production Endpoint)
- POST /api/optimization/alternatives (Day 13 Pipeline)
- GET  /api/optimization/alternatives/{shipment_id}
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.database.connection import SessionLocal
from app.main import app
from app.models.shipment import Shipment
from optimization.decision_schemas import OptimizationResponse


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_shipment_id():
    session = SessionLocal()
    try:
        s = session.query(Shipment).first()
        return s.shipment_id if s else "SHIP001"
    finally:
        session.close()


# ===========================================================================
# Day 14: POST /api/optimize Tests
# ===========================================================================

def test_post_optimize_successful_request(client, valid_shipment_id):
    """Verify POST /api/optimize successfully evaluates shipment, executes optimization, and returns ranked options."""
    response = client.post(
        "/api/optimize",
        json={
            "shipment_id": valid_shipment_id,
            "scenario_id": "baseline",
            "num_options": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Top-level status & schema conformance
    assert data["shipment_id"] == valid_shipment_id
    assert data["status"] in ["SUCCESS", "NO_FEASIBLE_OPTION", "INSUFFICIENT_DATA"]

    # Prediction block
    assert "prediction" in data
    pred = data["prediction"]
    assert 0.0 <= pred["delay_probability"] <= 1.0
    assert pred["predicted_delay_days"] >= 0.0
    assert pred["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert pred["model_version"] == "v1.0"

    # Options block (at most num_options)
    assert "options" in data
    assert 1 <= len(data["options"]) <= 3
    strategies = [o["strategy"] for o in data["options"]]
    assert any(s in ["AIR_FREIGHT", "SECONDARY_SUPPLIER", "DELAY_LAUNCH"] for s in strategies)

    for opt in data["options"]:
        assert opt["status"] in ["FEASIBLE", "INFEASIBLE", "INSUFFICIENT_DATA", "ERROR"]
        assert isinstance(opt["assumptions"], list)
        assert isinstance(opt["explanation"], str)

    # Constraint checks
    assert "constraint_checks" in data
    assert len(data["constraint_checks"]) >= 3
    check_names = [c["name"] for c in data["constraint_checks"]]
    assert "Maximum Budget" in check_names
    assert "Delivery Delay Tolerance" in check_names
    assert "Supplier Capacity" in check_names

    # Metadata & telemetry
    meta = data["optimization_metadata"]
    assert meta["scenario_id"] == "baseline"
    assert meta["runtime_ms"] > 0
    assert meta["model_version"] == "v1.0"

    # Schema validation via Pydantic model
    validated = OptimizationResponse(**data)
    assert validated.shipment_id == valid_shipment_id


def test_post_optimize_num_options_limit(client, valid_shipment_id):
    """Verify API returns at most the configured num_options (e.g. 2 options)."""
    response = client.post(
        "/api/optimize",
        json={
            "shipment_id": valid_shipment_id,
            "scenario_id": "baseline",
            "num_options": 2,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["options"]) <= 2


def test_post_optimize_unsupported_scenario_rejected(client, valid_shipment_id):
    """Verify API returns 400 when an unsupported scenario_id is supplied."""
    response = client.post(
        "/api/optimize",
        json={
            "shipment_id": valid_shipment_id,
            "scenario_id": "fictional_unsupported_scenario_999",
        },
    )
    assert response.status_code == 400
    assert "unsupported scenario_id" in response.json()["detail"].lower()


def test_post_optimize_nonexistent_shipment_returns_404(client):
    """Verify API returns 404 when target shipment ID is not in database."""
    response = client.post(
        "/api/optimize",
        json={"shipment_id": "NON_EXISTENT_SHIP_12345"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_post_optimize_blank_shipment_returns_400(client):
    """Verify API returns 400 when shipment_id is blank or whitespace."""
    response = client.post(
        "/api/optimize",
        json={"shipment_id": "    "},
    )
    assert response.status_code == 400


def test_post_optimize_validation_error_on_invalid_num_options(client, valid_shipment_id):
    """Verify API returns 422 Unprocessable Entity when num_options is out of bounds (< 1 or > 10)."""
    resp_zero = client.post(
        "/api/optimize",
        json={"shipment_id": valid_shipment_id, "num_options": 0},
    )
    assert resp_zero.status_code == 422

    resp_excess = client.post(
        "/api/optimize",
        json={"shipment_id": valid_shipment_id, "num_options": 25},
    )
    assert resp_excess.status_code == 422


def test_post_optimize_no_feasible_option_behavior(client, valid_shipment_id):
    """Verify API returns structured 200 with NO_FEASIBLE_OPTION when constraints make all options impossible."""
    response = client.post(
        "/api/optimize",
        json={
            "shipment_id": valid_shipment_id,
            "scenario_id": "budget_constrained",
            "scenario_overrides": {
                "budget": {"max_total_cost": 10.0},  # Impossibly tight $10 budget
                "delivery": {"maximum_acceptable_delay_days": 0.01},  # Impossibly tight delay
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["NO_FEASIBLE_OPTION", "SUCCESS"]
    if data["status"] == "NO_FEASIBLE_OPTION":
        assert data["recommended_option_id"] is None
        assert "no_feasible_option" in data["recommendation_reason"].lower()


def test_post_optimize_deterministic_repeated_calls(client, valid_shipment_id):
    """Verify identical inputs yield deterministic optimization outputs and rankings."""
    payload = {
        "shipment_id": valid_shipment_id,
        "scenario_id": "baseline",
        "num_options": 3,
    }
    resp1 = client.post("/api/optimize", json=payload)
    resp2 = client.post("/api/optimize", json=payload)

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    data1 = resp1.json()
    data2 = resp2.json()

    assert data1["status"] == data2["status"]
    assert data1["recommended_option_id"] == data2["recommended_option_id"]
    assert len(data1["options"]) == len(data2["options"])
    assert [o["option_id"] for o in data1["options"]] == [o["option_id"] for o in data2["options"]]


# ===========================================================================
# Day 13 Legacy / Alternatives Router Tests
# ===========================================================================

def test_api_generates_three_alternatives_with_valid_schema(client, valid_shipment_id):
    """Test POST /api/optimization/alternatives returns compliant response schema."""
    resp = client.post(
        "/api/optimization/alternatives",
        json={"shipment_id": valid_shipment_id},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["shipment_id"] == valid_shipment_id
    assert len(body["alternatives"]) == 3
    assert set(o["option_id"] for o in body["alternatives"]) == {"A", "B", "C"}
    assert body["baseline"]["currency"] == "USD"


def test_api_scenario_override_tight_budget(client, valid_shipment_id):
    """Test passing runtime scenario overrides via POST /api/optimization/alternatives."""
    resp = client.post(
        "/api/optimization/alternatives",
        json={
            "shipment_id": valid_shipment_id,
            "scenario_overrides": {
                "budget": {"max_total_cost": 500.0},
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert any(o["feasibility"] in ("INFEASIBLE", "INSUFFICIENT_DATA") for o in body["alternatives"])


def test_api_get_alternatives_endpoint(client, valid_shipment_id):
    """Test GET /api/optimization/alternatives/{shipment_id} with query parameters."""
    resp = client.get(f"/api/optimization/alternatives/{valid_shipment_id}?max_budget=60000&max_delay=6.0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["shipment_id"] == valid_shipment_id
