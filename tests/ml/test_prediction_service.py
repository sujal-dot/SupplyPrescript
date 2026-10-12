"""
SupplyPrescript — Unit and Integration Tests for PredictionService
==================================================================
Tests backend/app/services/prediction_service.py:
- Database record resolution (Supplier, Product, Inventory, Shipment statistics)
- Feature vector derivation conforming to Day 6 schema without target leakage
- Fallback logic for initial suppliers without shipment history (0.0 days)
- Operational risk tier classification boundaries (LOW, MEDIUM, HIGH)
- Error handling for missing entities, unavailable features, and model failures
- Backward-compatible legacy inference execution
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import HTTPException
from app.database.connection import SessionLocal
from app.models.supplier import Supplier
from app.models.product import Product
from app.schemas.prediction import PredictRequest, determine_risk_category
from app.services.prediction_service import PredictionService


@pytest.fixture
def db_session():
    """Provides a transactional database session for tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def base_predict_request():
    return PredictRequest(
        supplier_id=1,
        product_id=1,
        quantity=300,
        inventory_level=800,
        transport_mode="road",
    )


# ---------------------------------------------------------------------------
# 1. Feature Building and Database Resolution
# ---------------------------------------------------------------------------
def test_prediction_service_resolves_db_features(db_session, base_predict_request):
    """Verify PredictionService accurately retrieves supplier, product, and inventory features."""
    result = PredictionService.predict_shipment(base_predict_request, db_session)
    assert result is not None
    assert 0.0 <= result.delay_probability <= 1.0
    assert result.predicted_delay_days >= 0.0
    assert result.risk in ("LOW", "MEDIUM", "HIGH")
    assert result.model_version == "v1.0"
    assert result.prediction_id is not None

    features = result.features_used
    assert features["transport_mode"] == "Road"
    assert features["quantity"] == 300
    assert features["inventory_level"] == 800
    assert isinstance(features["supplier_reliability"], float)
    assert isinstance(features["historical_avg_delay"], float)
    assert isinstance(features["distance"], float)
    assert features["distance"] > 0


def test_prediction_service_with_custom_overrides(db_session):
    """Verify PredictionService uses request overrides when provided."""
    req = PredictRequest(
        supplier_id=1,
        product_id=1,
        quantity=150,
        inventory_level=400,
        transport_mode="Air",
        destination="Pune",
        shipping_cost=888.50,
        priority="High",
        lead_time=8,
        season="Winter",
        demand=550,
    )
    result = PredictionService.predict_shipment(req, db_session)
    features = result.features_used

    assert features["transport_mode"] == "Air"
    assert features["priority"] == "High"
    assert features["shipping_cost"] == 888.50
    assert features["lead_time"] == 8
    assert features["season"] == "Winter"
    assert features["demand"] == 550


def test_prediction_service_supplier_not_found(db_session):
    """Verify PredictionService raises 404 when supplier does not exist."""
    req = PredictRequest(
        supplier_id=999999,
        product_id=1,
        quantity=100,
        inventory_level=200,
        transport_mode="Road",
    )
    with pytest.raises(HTTPException) as exc_info:
        PredictionService.predict_shipment(req, db_session)
    assert exc_info.value.status_code == 404
    assert "Supplier with ID 999999 not found" in exc_info.value.detail


def test_prediction_service_product_not_found(db_session):
    """Verify PredictionService raises 404 when product does not exist."""
    req = PredictRequest(
        supplier_id=1,
        product_id=999999,
        quantity=100,
        inventory_level=200,
        transport_mode="Road",
    )
    with pytest.raises(HTTPException) as exc_info:
        PredictionService.predict_shipment(req, db_session)
    assert exc_info.value.status_code == 404
    assert "Product with ID 999999 not found" in exc_info.value.detail


def test_prediction_service_supplier_missing_reliability(db_session):
    """Verify PredictionService raises 400 if supplier has no reliability recorded."""
    mock_db = MagicMock()
    mock_supplier = MagicMock()
    mock_supplier.id = 1
    mock_supplier.supplier_id = "SUP001"
    mock_supplier.origin = "Bengaluru"
    mock_supplier.supplier_reliability = None
    mock_supplier.base_lead_time = 5

    mock_db.query.return_value.filter.return_value.first.return_value = mock_supplier

    req = PredictRequest(
        supplier_id=1,
        product_id=1,
        quantity=100,
        inventory_level=200,
        transport_mode="Road",
    )
    with pytest.raises(HTTPException) as exc_info:
        PredictionService.predict_shipment(req, mock_db)
    assert exc_info.value.status_code == 400
    assert "missing a reliability score" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 2. Neutral Baseline Fallback for Suppliers Without History
# ---------------------------------------------------------------------------
def test_prediction_service_new_supplier_fallback_to_zero(db_session):
    """Verify supplier without historical shipments receives 0.0 empirical delay."""
    new_sup = Supplier(
        supplier_id="TEST_NEW_SUP_99",
        supplier_name="Brand New Supplier",
        origin="Jaipur",
        supplier_reliability=Decimal("0.9200"),
        base_lead_time=4,
    )
    db_session.add(new_sup)
    db_session.commit()

    req = PredictRequest(
        supplier_id=new_sup.id,
        product_id=1,
        quantity=50,
        inventory_level=100,
        transport_mode="Road",
    )
    try:
        result = PredictionService.predict_shipment(req, db_session)
        assert result.features_used["historical_avg_delay"] == 0.0
        assert result.features_used["lead_time"] == 4
    finally:
        db_session.delete(new_sup)
        db_session.commit()


# ---------------------------------------------------------------------------
# 3. Risk Threshold Categorization
# ---------------------------------------------------------------------------
def test_determine_risk_category_logic():
    """Verify exact boundary categorization for risk levels."""
    # LOW: [0.0, 0.30)
    assert determine_risk_category(0.0) == "LOW"
    assert determine_risk_category(0.20) == "LOW"
    assert determine_risk_category(0.2999) == "LOW"

    # MEDIUM: [0.30, 0.70)
    assert determine_risk_category(0.30) == "MEDIUM"
    assert determine_risk_category(0.45) == "MEDIUM"
    assert determine_risk_category(0.6999) == "MEDIUM"

    # HIGH: [0.70, 1.0]
    assert determine_risk_category(0.70) == "HIGH"
    assert determine_risk_category(0.85) == "HIGH"
    assert determine_risk_category(1.0) == "HIGH"


# ---------------------------------------------------------------------------
# 4. Error Handling and Fail-Safes
# ---------------------------------------------------------------------------
def test_prediction_service_model_artifact_failure(db_session, base_predict_request):
    """Verify 503 Service Unavailable when model artifacts cannot be found."""
    with patch("app.services.prediction_service.predict_shipment", side_effect=FileNotFoundError("Missing v1.0.pkl")):
        with pytest.raises(HTTPException) as exc_info:
            PredictionService.predict_shipment(base_predict_request, db_session)
        assert exc_info.value.status_code == 503
        assert "Predictive ML model artifacts are unavailable" in exc_info.value.detail


def test_prediction_service_invalid_probability_guard(db_session, base_predict_request):
    """Verify ValueError is raised if model outputs invalid probability."""
    with patch("app.services.prediction_service.predict_shipment", return_value={"delay_probability": 1.5, "predicted_delay_days": 2.0}):
        with pytest.raises(HTTPException) as exc_info:
            PredictionService.predict_shipment(base_predict_request, db_session)
        assert exc_info.value.status_code == 400
