"""
SupplyPrescript — Integration Tests: Optimization & Prescriptive Alternatives API
=================================================================================
Tests FastAPI endpoints:
- POST /api/optimization/alternatives
- GET  /api/optimization/alternatives/{shipment_id}
- POST /api/optimize
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.database.connection import SessionLocal
from app.main import app
from app.models.shipment import Shipment


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_db_shipment():
    """Retrieve an authoritative existing shipment from PostgreSQL."""
    session = SessionLocal()
    try:
        shipment = session.query(Shipment).first()
        assert shipment is not None, "At least one shipment record should exist in test database"
        return shipment.shipment_id
    finally:
        session.close()


def test_post_optimization_alternatives_success(client, valid_db_shipment):
    """Verify POST /api/optimization/alternatives generates 3 alternatives for a valid shipment."""
    response = client.post(
        "/api/optimization/alternatives",
        json={
            "shipment_id": valid_db_shipment,
            "scenario_overrides": {
                "budget": {"max_total_cost": 50000.0},
            },
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["shipment_id"] == valid_db_shipment
    assert "baseline" in data
    assert "alternatives" in data
    assert len(data["alternatives"]) == 3

    # Check option IDs
    opt_ids = [opt["option_id"] for opt in data["alternatives"]]
    assert opt_ids == ["A", "B", "C"]

    # Check recommendation fields
    assert "recommendation_status" in data
    assert data["recommendation_status"] in ["FEASIBLE_RECOMMENDATION", "NO_FEASIBLE_OPTION"]
    assert "recommendation_reason" in data
    assert "trade_off_analysis" in data
    assert "evaluated_at" in data


def test_get_optimization_alternatives_by_id(client, valid_db_shipment):
    """Verify GET /api/optimization/alternatives/{shipment_id} returns evaluated alternatives."""
    response = client.get(f"/api/optimization/alternatives/{valid_db_shipment}?max_budget=45000&max_delay=5.0")
    assert response.status_code == 200
    data = response.json()

    assert data["shipment_id"] == valid_db_shipment
    assert len(data["alternatives"]) == 3
    assert data["baseline"]["currency"] == "USD"


def test_optimization_alternatives_nonexistent_shipment(client):
    """Verify 404 response for nonexistent shipment ID."""
    response = client.post(
        "/api/optimization/alternatives",
        json={"shipment_id": "NONEXISTENT_SHIP_9999"},
    )
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "not found" in detail.lower()


def test_optimization_alternatives_blank_shipment_id(client):
    """Verify 400 response for empty shipment ID."""
    response = client.post(
        "/api/optimization/alternatives",
        json={"shipment_id": "   "},
    )
    assert response.status_code == 400


def test_post_optimize_endpoint(client, valid_db_shipment):
    """Verify POST /api/optimize returns complete Day 14 prescriptive optimization response."""
    response = client.post(
        "/api/optimize",
        json={
            "shipment_id": valid_db_shipment,
            "scenario_id": "baseline",
            "num_options": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["shipment_id"] == valid_db_shipment
    assert "status" in data
    assert data["status"] in ["SUCCESS", "NO_FEASIBLE_OPTION"]
    assert "prediction" in data
    assert "options" in data
    assert len(data["options"]) <= 3
    assert "constraint_checks" in data
    assert "optimization_metadata" in data
