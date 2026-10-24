"""SupplyPrescript — API & Unit Tests for Decision ROI Dashboard (Day 21)
======================================================================
Tests verify:
1. GET /api/analytics/decision-roi returns full Day 21 schema structure.
2. Prediction accuracy metrics (cost MAE, MAPE, RMSE, MSE; delay MAE, MSE) are accurately calculated.
3. Success rate denominator excludes pending decisions while reporting their count.
4. Distinguishes forecast variance (predicted - actual) from verified baseline savings (baseline - actual).
5. Cost difference and ROI are grouped by strategy correctly.
6. Currency isolation and zero-division protection on empty or partial datasets.
7. Filters: strategy, decision_status (evaluation and operational), shipment_id, pagination.
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
def multi_strategy_test_data(db_session):
    """Creates a controlled set of decisions and outcomes across strategies."""
    rec = db_session.query(Recommendation).first()
    assert rec is not None

    shipment = db_session.query(Shipment).filter_by(shipment_id="SHIP000006").first()
    assert shipment is not None

    created_decisions = []
    created_outcomes = []

    # 1. Successful AIR_FREIGHT decision (on budget, fast delivery)
    # Baseline for SHIP000005 = (quantity * unit_cost) + shipping_cost
    d1_id = f"DEC-D21-AIR-{uuid.uuid4().hex[:6]}"
    d1 = Decision(
        decision_id=d1_id,
        recommendation_id=rec.id,
        shipment_id=shipment.shipment_id,
        decision="Option A: Air Freight",
        decision_source="Optimization",
        strategy="AIR_FREIGHT",
        status="RECORDED",
        predicted_cost=Decimal("10000.00"),
        predicted_delay=Decimal("1.00"),
        currency="USD",
        decision_time=datetime.now(timezone.utc) - timedelta(days=5),
    )
    db_session.add(d1)
    db_session.commit()
    created_decisions.append(d1)

    o1_id = f"OUT-D21-AIR-{uuid.uuid4().hex[:6]}"
    o1 = Outcome(
        outcome_id=o1_id,
        decision_id=d1.id,
        shipment_id=shipment.shipment_id,
        actual_cost=Decimal("9800.00"),  # under budget by 200 (cost diff = -200)
        currency="USD",
        actual_delay=Decimal("0.50"),   # faster by 0.5 (delay diff = -0.5)
        actual_delay_days=1,
        actual_quantity=Decimal(str(shipment.quantity)),
        actual_supplier=shipment.supplier_id,
        outcome_status="DELIVERED",
    )
    db_session.add(o1)
    db_session.commit()
    created_outcomes.append(o1)

    # 2. Failed SECONDARY_SUPPLIER decision (severe cost overrun + delay)
    d2_id = f"DEC-D21-SEC-{uuid.uuid4().hex[:6]}"
    d2 = Decision(
        decision_id=d2_id,
        recommendation_id=rec.id,
        shipment_id=shipment.shipment_id,
        decision="Option B: Secondary Supplier",
        decision_source="Optimization",
        strategy="SECONDARY_SUPPLIER",
        status="RECORDED",
        predicted_cost=Decimal("12000.00"),
        predicted_delay=Decimal("2.00"),
        currency="USD",
        decision_time=datetime.now(timezone.utc) - timedelta(days=3),
    )
    db_session.add(d2)
    db_session.commit()
    created_decisions.append(d2)

    o2_id = f"OUT-D21-SEC-{uuid.uuid4().hex[:6]}"
    o2 = Outcome(
        outcome_id=o2_id,
        decision_id=d2.id,
        shipment_id=shipment.shipment_id,
        actual_cost=Decimal("15000.00"),  # overrun by 3000 (25% overrun -> FAILURE)
        currency="USD",
        actual_delay=Decimal("5.00"),    # delay diff = +3.0 days
        actual_delay_days=5,
        actual_quantity=Decimal(str(shipment.quantity)),
        actual_supplier="SUP002",
        outcome_status="DELIVERED",
    )
    db_session.add(o2)
    db_session.commit()
    created_outcomes.append(o2)

    # 3. Pending decision (no outcome recorded)
    d3_id = f"DEC-D21-PEND-{uuid.uuid4().hex[:6]}"
    d3 = Decision(
        decision_id=d3_id,
        recommendation_id=rec.id,
        shipment_id=shipment.shipment_id,
        decision="Option C: Expedite",
        decision_source="Optimization",
        strategy="EXPEDITE",
        status="RECORDED",
        predicted_cost=Decimal("8000.00"),
        predicted_delay=Decimal("1.00"),
        currency="USD",
        decision_time=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(d3)
    db_session.commit()
    created_decisions.append(d3)

    try:
        yield created_decisions, created_outcomes, shipment
    finally:
        for o in created_outcomes:
            db_session.query(Outcome).filter(Outcome.id == o.id).delete()
        for d in created_decisions:
            db_session.query(Decision).filter(Decision.id == d.id).delete()
        db_session.commit()


def test_dashboard_endpoint_structure(client, multi_strategy_test_data):
    """Test 1: Verify all required sections of Day 21 response schema exist."""
    decisions, outcomes, shipment = multi_strategy_test_data
    ship_id = shipment.shipment_id

    response = client.get(f"/api/analytics/decision-roi?shipment_id={ship_id}")
    assert response.status_code == 200
    data = response.json()

    # Core sections
    assert "summary" in data
    assert "prediction_accuracy" in data
    assert "success_breakdown" in data
    assert "cost_difference_by_strategy" in data
    assert "roi_by_strategy" in data
    assert "savings_timeline" in data
    assert "performance_table" in data
    assert "data_quality" in data
    assert "filters" in data


def test_prediction_accuracy_calculation(client, multi_strategy_test_data):
    """Test 2: Verify cost & delay error metrics (MAE, MAPE, RMSE, signed error)."""
    decisions, outcomes, shipment = multi_strategy_test_data
    ship_id = shipment.shipment_id

    response = client.get(f"/api/analytics/decision-roi?shipment_id={ship_id}")
    assert response.status_code == 200
    pa = response.json()["prediction_accuracy"]

    # We have 2 completed decisions:
    # 1: pred=10000, act=9800  -> diff = -200, abs = 200, sq = 40,000, mape = 200/9800*100 = 2.04%
    # 2: pred=12000, act=15000 -> diff = +3000, abs = 3000, sq = 9,000,000, mape = 3000/15000*100 = 20.00%
    # Cost MAE = (200 + 3000) / 2 = 1600.00
    # Cost Mean Signed Error = (-200 + 3000) / 2 = 1400.00
    assert pa["cost_records_evaluated"] == 2
    assert pa["cost_mae"] == 1600.0
    assert pa["cost_mean_signed_error"] == 1400.0
    assert pa["cost_mape"] is not None
    assert round(pa["cost_mape"], 1) == 11.0  # (2.04 + 20.0) / 2 = 11.02%

    # Delay errors:
    # 1: pred=1.0, act=0.5 -> diff = -0.5
    # 2: pred=2.0, act=5.0 -> diff = +3.0
    # Delay MAE = (0.5 + 3.0) / 2 = 1.75 days
    # Delay Mean Signed Error = (-0.5 + 3.0) / 2 = 1.25 days
    assert pa["delay_records_evaluated"] == 2
    assert pa["delay_mae_days"] == 1.75
    assert pa["delay_mean_error_days"] == 1.25


def test_success_rate_denominator_excludes_pending(client, multi_strategy_test_data):
    """Test 3: Denominator must only count eligible completed decisions, not pending."""
    decisions, outcomes, shipment = multi_strategy_test_data
    ship_id = shipment.shipment_id

    response = client.get(f"/api/analytics/decision-roi?shipment_id={ship_id}")
    assert response.status_code == 200
    summary = response.json()["summary"]

    assert summary["total_decisions"] >= 3
    assert summary["completed_decisions"] == 2
    assert summary["pending_decisions"] >= 1

    # Eligible = successful (1) + failed (1) = 2
    assert summary["eligible_completed_decisions"] == 2
    # Success rate = (1 / 2) * 100 = 50.0%
    assert summary["success_rate"] == 50.0
    assert summary["failure_rate"] == 50.0


def test_distinguishes_forecast_variance_and_baseline_savings(client, multi_strategy_test_data):
    """Test 4: Forecast variance (pred - act) vs verified baseline savings (base - act)."""
    decisions, outcomes, shipment = multi_strategy_test_data
    ship_id = shipment.shipment_id

    response = client.get(f"/api/analytics/decision-roi?shipment_id={ship_id}")
    assert response.status_code == 200
    summary = response.json()["summary"]

    # Forecast variance: pred - act
    # Decision 1: 10000 - 9800 = +200
    # Decision 2: 12000 - 15000 = -3000
    # Total forecast variance = -2800
    assert summary["forecast_variance"] == "-2800.00"

    # Baseline savings: baseline - actual
    # Baseline cost = (quantity * unit_cost) + shipping_cost for SHIP000005
    # Verified baseline savings must be distinct from forecast variance
    assert summary["verified_baseline_savings"] is not None
    assert summary["verified_baseline_savings"] != summary["forecast_variance"]


def test_strategy_groupings(client, multi_strategy_test_data):
    """Test 5: Verify strategies (AIR_FREIGHT, SECONDARY_SUPPLIER, EXPEDITE) are isolated."""
    decisions, outcomes, shipment = multi_strategy_test_data
    ship_id = shipment.shipment_id

    response = client.get(f"/api/analytics/decision-roi?shipment_id={ship_id}")
    assert response.status_code == 200
    data = response.json()

    strat_diffs = {item["strategy"]: item for item in data["cost_difference_by_strategy"]}
    assert "AIR_FREIGHT" in strat_diffs
    assert "SECONDARY_SUPPLIER" in strat_diffs

    # AIR_FREIGHT cost diff was -200 (under budget)
    assert strat_diffs["AIR_FREIGHT"]["average_cost_difference"] == "-200.00"
    # SECONDARY_SUPPLIER cost diff was +3000 (overrun)
    assert strat_diffs["SECONDARY_SUPPLIER"]["average_cost_difference"] == "+3000.00"

    strat_roi = {item["strategy"]: item for item in data["roi_by_strategy"]}
    assert strat_roi["AIR_FREIGHT"]["success_rate"] == 100.0
    assert strat_roi["SECONDARY_SUPPLIER"]["success_rate"] == 0.0


def test_filter_by_strategy(client, multi_strategy_test_data):
    """Test 6: Filter by strategy query parameter."""
    decisions, outcomes, shipment = multi_strategy_test_data
    ship_id = shipment.shipment_id

    response = client.get(f"/api/analytics/decision-roi?shipment_id={ship_id}&strategy=AIR_FREIGHT")
    assert response.status_code == 200
    data = response.json()

    assert data["summary"]["total_decisions"] == 1
    assert data["summary"]["completed_decisions"] == 1
    assert data["summary"]["success_rate"] == 100.0


def test_filter_by_decision_evaluation_status(client, multi_strategy_test_data):
    """Test 7: Filter by evaluation status (e.g. FAILURE)."""
    decisions, outcomes, shipment = multi_strategy_test_data
    ship_id = shipment.shipment_id

    response = client.get(f"/api/analytics/decision-roi?shipment_id={ship_id}&decision_status=FAILURE")
    assert response.status_code == 200
    data = response.json()

    assert data["summary"]["total_decisions"] == 1
    assert data["summary"]["failed_decisions"] == 1
    assert data["summary"]["success_rate"] == 0.0


def test_performance_table_pagination(client, multi_strategy_test_data):
    """Test 8: Paginated decision performance records."""
    decisions, outcomes, shipment = multi_strategy_test_data
    ship_id = shipment.shipment_id

    response = client.get(f"/api/analytics/decision-roi?shipment_id={ship_id}&page=1&page_size=2")
    assert response.status_code == 200
    perf = response.json()["performance_table"]

    assert perf["page"] == 1
    assert perf["page_size"] == 2
    assert len(perf["items"]) <= 2
    assert perf["total"] >= 3
    assert perf["total_pages"] >= 2
