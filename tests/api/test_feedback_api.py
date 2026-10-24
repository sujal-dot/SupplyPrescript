"""SupplyPrescript — API Integration Tests for Model Feedback Pipeline (Day 22)
============================================================================
Tests verify:
1. POST /api/feedback/generate creates versioned feedback records and exports.
2. Idempotent repeated generation does not duplicate rows.
3. GET /api/feedback lists records with pagination and filters.
4. GET /api/feedback/{id} retrieves specific record or returns 404.
5. POST /api/feedback/evaluate computes statistical metrics (MAE, RMSE, bias).
6. POST /api/feedback/evaluate handles insufficient data without fabrication.
7. Verification that model evaluation does not alter production models.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.database.connection import SessionLocal
from app.models.prediction import Prediction
from app.models.model_version import ModelVersion
from app.models.recommendation import Recommendation
from app.models.decision import Decision
from app.models.outcome import Outcome
from app.models.shipment import Shipment
from app.models.feedback import Feedback


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
def setup_feedback_test_data(db_session):
    """Creates isolated predictions, decisions, and outcomes for feedback pipeline tests."""
    mv = db_session.query(ModelVersion).filter_by(version="v1.0.0").first()
    if not mv:
        mv = ModelVersion(
            model_name="delay_risk_classifier",
            version="v1.0.0",
            model_type="classifier",
            algorithm="XGBoost",
            is_active=True,
        )
        db_session.add(mv)
        db_session.commit()

    shipment = db_session.query(Shipment).filter_by(shipment_id="SHIP000007").first()
    if not shipment:
        shipment = db_session.query(Shipment).first()
    assert shipment is not None

    clean_ship_id = shipment.shipment_id

    # 1. Prediction 1 (Eligible: Predicted 2.0 days, Actual 3.5 days -> Error +1.5 days)
    p1_id = f"PRED-D22-1-{uuid.uuid4().hex[:6]}"
    pred1 = Prediction(
        prediction_id=p1_id,
        shipment_id=clean_ship_id,
        model_version_id=mv.id,
        prediction_type="Delivery Time",
        predicted_value=Decimal("2.0000"),
        prediction_probability=Decimal("0.8500"),
        prediction_status="Generated",
    )
    db_session.add(pred1)
    db_session.commit()

    rec1_id = f"REC-D22-1-{uuid.uuid4().hex[:6]}"
    rec1 = Recommendation(
        recommendation_id=rec1_id,
        prediction_id=pred1.id,
        recommendation_type="Expedite Shipment",
        recommendation_text="Expedite to avoid critical delay",
        recommended_action="Air freight option",
        confidence_score=Decimal("0.8500"),
        status="Active",
    )
    db_session.add(rec1)
    db_session.commit()

    dec1_id = f"DEC-D22-1-{uuid.uuid4().hex[:6]}"
    dec1 = Decision(
        decision_id=dec1_id,
        recommendation_id=rec1.id,
        shipment_id=clean_ship_id,
        decision="Option A: Air Freight",
        decision_source="Optimization",
        status="RECORDED",
        predicted_delay=Decimal("2.00"),
        predicted_cost=Decimal("12000.00"),
    )
    db_session.add(dec1)
    db_session.commit()

    out1_id = f"OUT-D22-1-{uuid.uuid4().hex[:6]}"
    out1 = Outcome(
        outcome_id=out1_id,
        decision_id=dec1.id,
        shipment_id=clean_ship_id,
        actual_delay=Decimal("3.50"),
        actual_cost=Decimal("12500.00"),
        outcome_status="DELIVERED",
    )
    db_session.add(out1)
    db_session.commit()

    # 2. Prediction 2 (Eligible: Predicted 4.0 days, Actual 2.0 days -> Error -2.0 days)
    p2_id = f"PRED-D22-2-{uuid.uuid4().hex[:6]}"
    pred2 = Prediction(
        prediction_id=p2_id,
        shipment_id=clean_ship_id,
        model_version_id=mv.id,
        prediction_type="Delivery Time",
        predicted_value=Decimal("4.0000"),
        prediction_probability=Decimal("0.7500"),
        prediction_status="Generated",
    )
    db_session.add(pred2)
    db_session.commit()

    rec2_id = f"REC-D22-2-{uuid.uuid4().hex[:6]}"
    rec2 = Recommendation(
        recommendation_id=rec2_id,
        prediction_id=pred2.id,
        recommendation_type="Change Supplier",
        recommendation_text="Use backup supplier",
        recommended_action="Secondary supplier",
        confidence_score=Decimal("0.8000"),
        status="Active",
    )
    db_session.add(rec2)
    db_session.commit()

    dec2_id = f"DEC-D22-2-{uuid.uuid4().hex[:6]}"
    dec2 = Decision(
        decision_id=dec2_id,
        recommendation_id=rec2.id,
        shipment_id=clean_ship_id,
        decision="Option B: Secondary Supplier",
        decision_source="Optimization",
        status="RECORDED",
        predicted_delay=Decimal("4.00"),
        predicted_cost=Decimal("9000.00"),
    )
    db_session.add(dec2)
    db_session.commit()

    out2_id = f"OUT-D22-2-{uuid.uuid4().hex[:6]}"
    out2 = Outcome(
        outcome_id=out2_id,
        decision_id=dec2.id,
        shipment_id=clean_ship_id,
        actual_delay=Decimal("2.00"),
        actual_cost=Decimal("8800.00"),
        outcome_status="DELIVERED",
    )
    db_session.add(out2)
    db_session.commit()

    # 3. Prediction 3 (Pending: No outcome recorded yet)
    p3_id = f"PRED-D22-3-{uuid.uuid4().hex[:6]}"
    pred3 = Prediction(
        prediction_id=p3_id,
        shipment_id=clean_ship_id,
        model_version_id=mv.id,
        prediction_type="Delivery Time",
        predicted_value=Decimal("1.5000"),
        prediction_probability=Decimal("0.9000"),
        prediction_status="Generated",
    )
    db_session.add(pred3)
    db_session.commit()

    try:
        yield {
            "model_version": "v1.0.0",
            "shipment_id": clean_ship_id,
            "pred1": pred1,
            "pred2": pred2,
            "pred3": pred3,
            "out1": out1,
            "out2": out2,
        }
    finally:
        # Cleanup
        db_session.query(Feedback).filter(Feedback.prediction_id.in_([p1_id, p2_id, p3_id])).delete(synchronize_session=False)
        db_session.query(Outcome).filter(Outcome.id.in_([out1.id, out2.id])).delete(synchronize_session=False)
        db_session.query(Decision).filter(Decision.id.in_([dec1.id, dec2.id])).delete(synchronize_session=False)
        db_session.query(Recommendation).filter(Recommendation.id.in_([rec1.id, rec2.id])).delete(synchronize_session=False)
        db_session.query(Prediction).filter(Prediction.id.in_([pred1.id, pred2.id, pred3.id])).delete(synchronize_session=False)
        db_session.commit()


def test_generate_feedback_endpoint(client, setup_feedback_test_data):
    """Test 1: POST /api/feedback/generate processes records and exports manifest."""
    data = setup_feedback_test_data

    response = client.post("/api/feedback/generate", json={"export_dataset": True})
    assert response.status_code == 200
    res_json = response.json()

    assert res_json["processed_count"] >= 3
    assert res_json["eligible_count"] >= 2
    assert res_json["pending_count"] >= 1
    assert res_json["dataset_version"] is not None


def test_repeated_generation_is_idempotent(client, setup_feedback_test_data, db_session):
    """Test 2: Repeated generation runs update records without creating duplicates."""
    data = setup_feedback_test_data

    # First run
    res1 = client.post("/api/feedback/generate", json={"export_dataset": False})
    assert res1.status_code == 200

    count_after_first = db_session.query(Feedback).count()

    # Second run
    res2 = client.post("/api/feedback/generate", json={"export_dataset": False})
    assert res2.status_code == 200

    count_after_second = db_session.query(Feedback).count()
    assert count_after_first == count_after_second


def test_list_feedback_endpoint_with_filters(client, setup_feedback_test_data):
    """Test 3: GET /api/feedback lists records and applies filters."""
    data = setup_feedback_test_data
    client.post("/api/feedback/generate", json={"export_dataset": False})

    # List all
    response = client.get(f"/api/feedback?shipment_id={data['shipment_id']}")
    assert response.status_code == 200
    res = response.json()

    assert "items" in res
    assert "summary_counts" in res
    assert res["summary_counts"]["total"] >= 3
    assert res["summary_counts"]["eligible"] >= 2

    # Filter by status ELIGIBLE
    res_eligible = client.get(f"/api/feedback?shipment_id={data['shipment_id']}&feedback_status=ELIGIBLE").json()
    for it in res_eligible["items"]:
        assert it["feedback_status"] == "ELIGIBLE"
        assert it["prediction_error"] is not None

    # Filter by status PENDING_OUTCOME
    res_pending = client.get(f"/api/feedback?shipment_id={data['shipment_id']}&feedback_status=PENDING_OUTCOME").json()
    for it in res_pending["items"]:
        assert it["feedback_status"] == "PENDING_OUTCOME"
        assert it["actual_delay"] is None


def test_get_feedback_by_id(client, setup_feedback_test_data):
    """Test 4: GET /api/feedback/{id} returns specific record."""
    data = setup_feedback_test_data
    client.post("/api/feedback/generate", json={"export_dataset": False})

    # Find created feedback item
    list_res = client.get(f"/api/feedback?shipment_id={data['shipment_id']}").json()
    target_id = list_res["items"][0]["feedback_id"]

    res = client.get(f"/api/feedback/{target_id}")
    assert res.status_code == 200
    item = res.json()
    assert item["feedback_id"] == target_id
    assert item["shipment_id"] == data["shipment_id"]


def test_get_feedback_nonexistent_returns_404(client):
    """Test 5: Nonexistent feedback ID returns 404."""
    response = client.get("/api/feedback/FB-NONEXISTENT-999")
    assert response.status_code == 404


def test_evaluate_model_accuracy(client, setup_feedback_test_data):
    """Test 6: POST /api/feedback/evaluate computes statistical metrics."""
    data = setup_feedback_test_data
    client.post("/api/feedback/generate", json={"export_dataset": False})

    # In setup data:
    # Pred 1: pred=2.0, act=3.5 -> error = +1.5, abs = 1.5
    # Pred 2: pred=4.0, act=2.0 -> error = -2.0, abs = 2.0
    # On these two: MAE = (1.5 + 2.0) / 2 = 1.75
    # Mean Signed Error = (+1.5 - 2.0) / 2 = -0.25
    response = client.post("/api/feedback/evaluate", json={
        "model_version": "v1.0.0",
        "min_sample_threshold": 10,
    })
    assert response.status_code == 200
    res = response.json()

    assert res["status"] == "EVALUATED"
    assert res["evaluated_count"] >= 2
    assert res["mae"] is not None
    assert res["rmse"] is not None
    assert res["mean_signed_error"] is not None
    assert res["median_absolute_error"] is not None
    assert res["is_preliminary"] is True  # Count < 10 threshold
    assert any("preliminary" in w.lower() for w in res["warnings"])
    assert "error_sign_convention" in res


def test_evaluate_model_insufficient_data(client):
    """Test 7: Evaluation for model version with no data returns INSUFFICIENT_DATA."""
    response = client.post("/api/feedback/evaluate", json={
        "model_version": "v999.0.0",
        "min_sample_threshold": 5,
    })
    assert response.status_code == 200
    res = response.json()

    assert res["status"] == "INSUFFICIENT_DATA"
    assert res["evaluated_count"] == 0
    assert res["mae"] is None
    assert res["rmse"] is None


def test_model_evaluation_does_not_modify_production_models(client, setup_feedback_test_data, db_session):
    """Test 8: Model evaluation is strictly read-only and never promotes or modifies models."""
    active_before = [mv.version for mv in db_session.query(ModelVersion).filter_by(is_active=True).all()]

    client.post("/api/feedback/evaluate", json={
        "model_version": "v1.0.0",
    })

    active_after = [mv.version for mv in db_session.query(ModelVersion).filter_by(is_active=True).all()]
    assert active_before == active_after
