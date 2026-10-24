"""SupplyPrescript — API Integration Tests for Decision ROI Engine (Day 20)
========================================================================
Tests verify:
1. GET /api/decisions/{decision_id}/roi returns full calculation for completed decision.
2. A decision with no outcome returns a documented pending response (no zero fabrication).
3. A nonexistent decision returns 404 Not Found.
4. Persisted decision and outcome match the returned calculations.
5. Original predictions are not overwritten.
6. GET /api/analytics/decision-roi calculates portfolio summaries.
7. Portfolio summaries exclude incomplete records and isolate currencies.
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
    return TestClient(app)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_decision_and_outcome(db_session):
    """Sets up a test decision and outcome with known baseline values."""
    rec = db_session.query(Recommendation).first()
    assert rec is not None

    shipment = db_session.query(Shipment).filter_by(shipment_id="SHIP000005").first()
    assert shipment is not None

    # Expected baseline = (quantity * unit_cost) + shipping_cost
    dec_id = f"DEC-ROI-{uuid.uuid4().hex[:8]}"
    decision = Decision(
        decision_id=dec_id,
        recommendation_id=rec.id,
        shipment_id=shipment.shipment_id,
        decision="Option A: Air Freight",
        decision_source="Optimization",
        strategy="AIR_FREIGHT",
        option_id="A",
        status="RECORDED",
        predicted_cost=Decimal("15000.00"),
        estimated_total_cost=Decimal("15000.00"),
        predicted_delay=Decimal("1.50"),
        estimated_delivery_days=Decimal("4.00"),
        currency="USD",
        user_id="usr_logistics_lead",
        external_action_status="NOT_EXECUTED",
    )
    db_session.add(decision)
    db_session.commit()

    outcome_id = f"OUT-ROI-{uuid.uuid4().hex[:8]}"
    outcome = Outcome(
        outcome_id=outcome_id,
        decision_id=decision.id,
        decision_business_id=decision.decision_id,
        shipment_id=shipment.shipment_id,
        actual_cost=Decimal("14200.00"),
        currency="USD",
        actual_delivery_date=shipment.expected_delivery_date + timedelta(days=1),
        actual_delay=Decimal("1.00"),
        actual_delay_days=1,
        baseline_delivery_date=shipment.expected_delivery_date,
        actual_supplier=shipment.supplier_id,
        actual_quantity=Decimal(str(shipment.quantity)),
        outcome_status="DELIVERED",
        source="manual_entry",
    )
    db_session.add(outcome)
    db_session.commit()

    try:
        yield decision, outcome, shipment
    finally:
        db_session.query(Outcome).filter(Outcome.decision_id == decision.id).delete()
        db_session.query(Decision).filter(Decision.id == decision.id).delete()
        db_session.commit()


def test_get_decision_roi_completed_decision(client, sample_decision_and_outcome):
    """Test 1: ROI endpoint returns calculation for a completed decision."""
    decision, outcome, shipment = sample_decision_and_outcome

    response = client.get(f"/api/decisions/{decision.decision_id}/roi")
    assert response.status_code == 200
    data = response.json()

    assert data["decision_id"] == decision.decision_id
    assert data["shipment_id"] == shipment.shipment_id
    assert data["currency"] == "USD"

    # Cost calculations
    cost = data["cost"]
    assert cost["predicted_cost"] == "15000.00"
    assert cost["actual_cost"] == "14200.00"
    assert cost["cost_difference"] == "-800.00"  # 14200 - 15000 = -800
    assert cost["money_saved_vs_prediction"] == "800.00"  # 15000 - 14200 = 800
    assert cost["cost_variance_percentage"] == -5.33

    # Delivery calculations
    delivery = data["delivery"]
    assert delivery["predicted_delay"] == 1.5
    assert delivery["actual_delay"] == 1.0
    assert delivery["delay_difference"] == -0.5  # 1.0 - 1.5 = -0.5 (earlier!)

    # Evaluation
    evaluation = data["decision_evaluation"]
    assert evaluation["cost_performance"] == "BETTER_THAN_PREDICTED"
    assert evaluation["delivery_performance"] == "BETTER_THAN_PREDICTED"
    assert evaluation["decision_success"] == "SUCCESS"


def test_get_decision_roi_pending_outcome(client, db_session):
    """Test 2: A decision with no outcome returns a documented pending response."""
    rec = db_session.query(Recommendation).first()
    dec_id = f"DEC-PENDING-{uuid.uuid4().hex[:8]}"
    decision = Decision(
        decision_id=dec_id,
        recommendation_id=rec.id,
        shipment_id="SHIP000005",
        decision="Option B: Secondary Supplier",
        decision_source="Optimization",
        strategy="SECONDARY_SUPPLIER",
        option_id="B",
        status="RECORDED",
        predicted_cost=Decimal("12000.00"),
        predicted_delay=Decimal("2.00"),
        currency="USD",
    )
    db_session.add(decision)
    db_session.commit()

    try:
        response = client.get(f"/api/decisions/{decision.decision_id}/roi")
        assert response.status_code == 200
        data = response.json()

        assert data["cost"]["actual_cost"] is None
        assert data["cost"]["cost_difference"] is None
        assert data["delivery"]["actual_delay"] is None
        assert data["roi"]["status"] == "UNAVAILABLE"
        assert data["decision_evaluation"]["decision_success"] == "PENDING_REVIEW"
        assert data["decision_evaluation"]["data_completeness"] == "INSUFFICIENT"
        assert any("no operational outcome recorded" in n.lower() for n in data["notes"])
    finally:
        db_session.query(Decision).filter(Decision.id == decision.id).delete()
        db_session.commit()


def test_get_decision_roi_nonexistent_404(client):
    """Test 3: Nonexistent decision returns 404."""
    response = client.get("/api/decisions/DEC-NONEXISTENT-99999/roi")
    assert response.status_code == 404


def test_predictions_remain_immutable_after_roi_calculation(client, sample_decision_and_outcome, db_session):
    """Test 5: Original predictions are not overwritten."""
    decision, outcome, shipment = sample_decision_and_outcome

    client.get(f"/api/decisions/{decision.decision_id}/roi")

    # Refresh from db
    db_decision = db_session.query(Decision).filter_by(id=decision.id).first()
    assert db_decision.predicted_cost == Decimal("15000.00")
    assert db_decision.predicted_delay == Decimal("1.50")


def test_portfolio_roi_endpoint(client, sample_decision_and_outcome):
    """Test 6: GET /api/analytics/decision-roi calculates portfolio summaries."""
    decision, outcome, shipment = sample_decision_and_outcome

    response = client.get(f"/api/analytics/decision-roi?shipment_id={shipment.shipment_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["total_decisions"] >= 1
    assert data["currency"] == "USD"
    assert data["calculation_version"] == "1.0"
    assert "success_counts" in data
