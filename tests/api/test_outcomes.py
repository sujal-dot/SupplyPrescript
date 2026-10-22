"""SupplyPrescript — API Integration Tests for Actual Outcome Tracking (Day 19)
==============================================================================
Tests verify:
- POST /api/decisions/{decision_id}/outcome creates and persists actual outcomes
- One-to-one constraint and 409 Conflict rejection for duplicate outcomes
- 404 Not Found for nonexistent decision or unrecorded outcome
- Proper calculation of actual delay from baseline date without fabrication
- Safe handling of undelivered shipments, zero predicted costs, and currency mismatches
- GET /api/decisions/{decision_id}/outcome retrieves comparison
- GET /api/outcomes lists records with pagination and filters
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.database.connection import SessionLocal
from app.models.decision import Decision
from app.models.outcome import Outcome
from app.models.shipment import Shipment
from app.models.recommendation import Recommendation


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Provides a transactional database session for setup & teardown."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_decision(db_session):
    """Fixture ensuring a valid, isolated Decision record exists using existing baseline shipment."""
    rec = db_session.query(Recommendation).first()
    assert rec is not None, "A baseline recommendation must exist in database"

    shipment = db_session.query(Shipment).filter_by(shipment_id="SHIP000005").first()
    assert shipment is not None, "SHIP000005 must exist"

    dc_id = f"DEC-TEST-OUT-{uuid.uuid4().hex[:8]}"
    decision = Decision(
        decision_id=dc_id,
        recommendation_id=rec.id,
        shipment_id="SHIP000005",
        decision="Option A: Air Freight",
        decision_source="Optimization",
        strategy="AIR_FREIGHT",
        option_id="A",
        status="RECORDED",
        predicted_cost=Decimal("15000.00"),
        estimated_total_cost=Decimal("15000.00"),
        predicted_delay=Decimal("1.00"),
        estimated_delivery_days=Decimal("4.00"),
        currency="USD",
        user_id="usr_logistics_lead",
        external_action_status="NOT_EXECUTED",
    )
    db_session.add(decision)
    db_session.commit()

    try:
        yield decision
    finally:
        db_session.query(Outcome).filter(Outcome.decision_id == decision.id).delete()
        db_session.query(Decision).filter(Decision.id == decision.id).delete()
        db_session.commit()


def test_record_outcome_success(client, test_decision, db_session):
    """Test POST /api/decisions/{decision_id}/outcome with valid actual data."""
    shipment = db_session.query(Shipment).filter_by(shipment_id="SHIP000005").first()
    baseline = shipment.expected_delivery_date
    actual_d = baseline + timedelta(days=2)

    payload = {
        "actual_cost": 16200.00,
        "currency": "USD",
        "actual_delivery_date": actual_d.isoformat(),
        "actual_supplier": "SUPPLIER_EXPEDITED",
        "actual_quantity": float(shipment.quantity),
        "source": "manual_entry",
        "notes": "Flight expedited with minor fuel surcharge.",
    }

    res = client.post(f"/api/decisions/{test_decision.decision_id}/outcome", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["decision_id"] == test_decision.decision_id
    assert data["shipment_id"] == "SHIP000005"

    # Verify Predictions snapshot
    assert data["predicted"]["predicted_cost"] == 15000.00
    assert data["predicted"]["predicted_delay"] == 1.00
    assert data["predicted"]["planned_quantity"] == float(shipment.quantity)
    assert data["predicted"]["currency"] == "USD"

    # Verify Actuals snapshot
    actual = data["actual"]
    assert actual["actual_cost"] == 16200.00
    assert actual["actual_delivery_date"] == actual_d.isoformat()
    assert actual["actual_delay"] == 2.0
    assert actual["actual_quantity"] == float(shipment.quantity)
    assert actual["outcome_status"] == "DELIVERED"
    assert actual["source"] == "manual_entry"

    # Verify Variances
    var = data["variance"]
    assert var["cost_variance"] == 1200.00  # 16200 - 15000
    assert var["cost_variance_percentage"] == 8.00  # (1200 / 15000) * 100
    assert var["delay_variance"] == 1.00  # actual_delay (2) - predicted_delay (1)
    assert var["quantity_variance"] == 0.00
    assert data["data_completeness"] == "COMPLETE"


def test_record_outcome_nonexistent_decision_rejected(client):
    """Test POST /api/decisions/{decision_id}/outcome with unknown decision returns 404."""
    payload = {
        "actual_cost": 10000.00,
        "actual_delivery_date": "2026-10-15",
    }
    res = client.post("/api/decisions/NONEXISTENT_DEC_99999/outcome", json=payload)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_record_outcome_duplicate_rejected(client, test_decision):
    """Test that a second outcome submission for the same decision returns 409 Conflict."""
    payload1 = {
        "actual_cost": 12000.00,
        "actual_delivery_date": "2026-10-10",
    }
    res1 = client.post(f"/api/decisions/{test_decision.decision_id}/outcome", json=payload1)
    assert res1.status_code == 201

    payload2 = {
        "actual_cost": 13000.00,
        "actual_delivery_date": "2026-10-11",
    }
    res2 = client.post(f"/api/decisions/{test_decision.decision_id}/outcome", json=payload2)
    assert res2.status_code == 409
    assert "already been recorded" in res2.json()["detail"]


def test_record_outcome_negative_cost_rejected(client, test_decision):
    """Test validation rejection for negative actual cost."""
    payload = {
        "actual_cost": -50.00,
    }
    res = client.post(f"/api/decisions/{test_decision.decision_id}/outcome", json=payload)
    assert res.status_code == 422


def test_actual_delay_calculation_early_delivery(client, test_decision, db_session):
    """Test that arriving before baseline expected date produces actual_delay = 0."""
    shipment = db_session.query(Shipment).filter_by(shipment_id="SHIP000005").first()
    early_d = shipment.expected_delivery_date - timedelta(days=2)

    payload = {
        "actual_cost": 14000.00,
        "actual_delivery_date": early_d.isoformat(),
    }
    res = client.post(f"/api/decisions/{test_decision.decision_id}/outcome", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["actual"]["actual_delay"] == 0.0
    # Cost variance is negative (savings of $1,000)
    assert data["variance"]["cost_variance"] == -1000.00
    # Delay variance is negative (actual delay 0 vs predicted delay 1)
    assert data["variance"]["delay_variance"] == -1.00


def test_undelivered_shipment_handles_delay_safely(client, test_decision):
    """Test that undelivered shipments without actual_delivery_date leave delay unset."""
    payload = {
        "actual_cost": 15000.00,
        "actual_delivery_date": None,
        "outcome_status": "AWAITING_DELIVERY",
        "notes": "Shipment in transit; partial booking invoice received.",
    }
    res = client.post(f"/api/decisions/{test_decision.decision_id}/outcome", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["actual"]["actual_delivery_date"] is None
    assert data["actual"]["actual_delay"] is None
    assert data["actual"]["outcome_status"] == "AWAITING_DELIVERY"
    assert data["variance"]["delay_variance"] is None
    assert data["data_completeness"] == "PARTIAL"


def test_currency_mismatch_handled_safely(client, test_decision):
    """Test currency mismatch skips cost variance and provides explanation note."""
    payload = {
        "actual_cost": 12500.00,
        "currency": "EUR",  # Decision is in USD
        "actual_delivery_date": "2026-10-11",
    }
    res = client.post(f"/api/decisions/{test_decision.decision_id}/outcome", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["variance"]["cost_variance"] is None
    assert data["variance"]["cost_variance_percentage"] is None
    assert any("currency mismatch" in n.lower() for n in data["notes"])


def test_get_decision_outcome_success(client, test_decision):
    """Test GET /api/decisions/{decision_id}/outcome retrieves recorded comparison."""
    # First record outcome
    post_res = client.post(
        f"/api/decisions/{test_decision.decision_id}/outcome",
        json={"actual_cost": 15500.00, "actual_delivery_date": "2026-10-11"},
    )
    assert post_res.status_code == 201

    # Then retrieve it
    get_res = client.get(f"/api/decisions/{test_decision.decision_id}/outcome")
    assert get_res.status_code == 200
    data = get_res.json()

    assert data["decision_id"] == test_decision.decision_id
    assert data["actual"]["actual_cost"] == 15500.00
    assert data["variance"]["cost_variance"] == 500.00


def test_get_decision_outcome_not_recorded_404(client, test_decision):
    """Test GET /api/decisions/{decision_id}/outcome returns 404 when unrecorded."""
    res = client.get(f"/api/decisions/{test_decision.decision_id}/outcome")
    assert res.status_code == 404
    assert "no operational outcome has been recorded" in res.json()["detail"].lower()


def test_get_outcomes_list_and_filters(client, test_decision):
    """Test GET /api/outcomes lists records with pagination and filters."""
    # Record an outcome
    client.post(
        f"/api/decisions/{test_decision.decision_id}/outcome",
        json={
            "actual_cost": 15000.00,
            "actual_supplier": "UNIQUE_FILTER_SUPPLIER",
            "actual_delivery_date": "2026-10-10",
            "outcome_status": "DELIVERED",
        },
    )

    # Query with supplier filter
    res = client.get("/api/outcomes", params={"supplier": "UNIQUE_FILTER_SUPPLIER"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any(item["actual_supplier"] == "UNIQUE_FILTER_SUPPLIER" for item in data["items"])

    # Query with pagination limit
    res_page = client.get("/api/outcomes", params={"limit": 1, "offset": 0})
    assert res_page.status_code == 200
    data_page = res_page.json()
    assert len(data_page["items"]) <= 1
    assert data_page["limit"] == 1
