"""
SupplyPrescript — API Integration Tests for POST /api/predict
=============================================================
Tests the production shipment delay prediction endpoint:
- Successful end-to-end inference with real database records and registered ML models
- Strict request schema validation (required fields, positive quantities, non-negative inventory)
- Rejection of unexpected fields and target leakage fields (actual_delivery_date, delay_days)
- Database entity validation (404 for unknown supplier/product, 400 for missing features)
- Risk category operational threshold boundary checks (0.2999 -> LOW, 0.30 -> MEDIUM, 0.70 -> HIGH)
- Model artifact availability and failure handling (503 Service Unavailable)
- Backward compatibility for legacy POST /api/predictions/shipment-delay endpoint
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch
import pytest

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.schemas.prediction import determine_risk_category

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def valid_predict_payload() -> dict:
    """Standard valid prediction request payload."""
    return {
        "supplier_id": 1,
        "product_id": 1,
        "quantity": 500,
        "inventory_level": 1200,
        "transport_mode": "air",
    }


# ---------------------------------------------------------------------------
# 1. Successful Predictions
# ---------------------------------------------------------------------------
def test_predict_endpoint_success(valid_predict_payload):
    """Verify POST /api/predict returns 200 with complete structured schema."""
    response = client.post("/api/predict", json=valid_predict_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    assert "delay_probability" in data
    assert "predicted_delay_days" in data
    assert "risk" in data
    assert "model_version" in data
    assert "prediction_id" in data
    assert "prediction_timestamp" in data
    assert "features_used" in data

    # Value ranges and types
    assert isinstance(data["delay_probability"], float)
    assert 0.0 <= data["delay_probability"] <= 1.0

    assert isinstance(data["predicted_delay_days"], float)
    assert data["predicted_delay_days"] >= 0.0

    assert data["risk"] in ("LOW", "MEDIUM", "HIGH")
    assert data["model_version"] == "v1.0"
    assert data["prediction_id"].startswith("PRED-")

    # Features used verification
    features = data["features_used"]
    assert features["transport_mode"] == "Air"  # Normalized to canonical Title case
    assert features["quantity"] == 500
    assert features["inventory_level"] == 1200
    assert features["supplier_reliability"] > 0
    assert features["distance"] > 0


def test_predict_endpoint_with_optional_overrides(valid_predict_payload):
    """Verify endpoint accepts and respects optional scenario planning inputs."""
    payload = valid_predict_payload.copy()
    payload.update({
        "destination": "Mumbai",
        "priority": "Critical",
        "shipping_cost": 350.50,
        "lead_time": 4,
        "season": "Summer",
        "demand": 450,
    })
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200

    data = response.json()
    features = data["features_used"]
    assert features["priority"] == "Critical"
    assert features["shipping_cost"] == 350.50
    assert features["lead_time"] == 4
    assert features["season"] == "Summer"
    assert features["demand"] == 450


def test_predict_endpoint_transport_mode_casing():
    """Verify case-insensitivity: 'road', 'ROAD', 'Road' all map to canonical 'Road'."""
    for mode in ["road", "ROAD", "Road", "rOaD"]:
        payload = {
            "supplier_id": 1,
            "product_id": 1,
            "quantity": 100,
            "inventory_level": 500,
            "transport_mode": mode,
        }
        response = client.post("/api/predict", json=payload)
        assert response.status_code == 200
        assert response.json()["features_used"]["transport_mode"] == "Road"


# ---------------------------------------------------------------------------
# 2. Request Schema Validation (422 Unprocessable Entity)
# ---------------------------------------------------------------------------
def test_predict_missing_required_fields():
    """Verify missing required fields trigger 422 Unprocessable Entity."""
    required_fields = ["supplier_id", "product_id", "quantity", "inventory_level", "transport_mode"]
    base_payload = {
        "supplier_id": 1,
        "product_id": 1,
        "quantity": 100,
        "inventory_level": 50,
        "transport_mode": "air",
    }

    for field in required_fields:
        payload = base_payload.copy()
        del payload[field]
        response = client.post("/api/predict", json=payload)
        assert response.status_code == 422, f"Expected 422 for missing {field}, got {response.status_code}"


def test_predict_negative_or_zero_quantity():
    """Verify quantity <= 0 is rejected with 422."""
    for qty in [0, -1, -500]:
        payload = {
            "supplier_id": 1,
            "product_id": 1,
            "quantity": qty,
            "inventory_level": 100,
            "transport_mode": "rail",
        }
        response = client.post("/api/predict", json=payload)
        assert response.status_code == 422


def test_predict_negative_inventory_level():
    """Verify negative inventory level is rejected with 422."""
    payload = {
        "supplier_id": 1,
        "product_id": 1,
        "quantity": 100,
        "inventory_level": -1,
        "transport_mode": "rail",
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_predict_invalid_transport_mode():
    """Verify invalid transport modalities are rejected with 422."""
    for bad_mode in ["rocket", "hyperloop", "walk", "123", ""]:
        payload = {
            "supplier_id": 1,
            "product_id": 1,
            "quantity": 100,
            "inventory_level": 50,
            "transport_mode": bad_mode,
        }
        response = client.post("/api/predict", json=payload)
        assert response.status_code == 422


def test_predict_invalid_supplier_or_product_ids():
    """Verify non-positive supplier and product IDs are rejected with 422."""
    for bad_id in [0, -1, -99]:
        # Invalid supplier_id
        res_sup = client.post("/api/predict", json={
            "supplier_id": bad_id,
            "product_id": 1,
            "quantity": 100,
            "inventory_level": 50,
            "transport_mode": "road",
        })
        assert res_sup.status_code == 422

        # Invalid product_id
        res_prod = client.post("/api/predict", json={
            "supplier_id": 1,
            "product_id": bad_id,
            "quantity": 100,
            "inventory_level": 50,
            "transport_mode": "road",
        })
        assert res_prod.status_code == 422


def test_predict_rejects_extra_fields(valid_predict_payload):
    """Verify unexpected extra fields are forbidden and rejected with 422."""
    payload = valid_predict_payload.copy()
    payload["unrecognized_parameter"] = "exploit"
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_predict_strictly_rejects_target_leakage_fields(valid_predict_payload):
    """Verify future delivery and target outcomes cannot enter the model."""
    leakage_fields = [
        ("actual_delivery_date", "2026-10-15"),
        ("actual_delay_days", 5),
        ("delay_days", 4),
        ("delayed", True),
        ("is_delayed", 1),
        ("delivery_status", "Delayed"),
        ("delay_reason", "Weather"),
        ("outcome", "Failed"),
        ("success_score", 0.8),
    ]

    for key, val in leakage_fields:
        payload = valid_predict_payload.copy()
        payload[key] = val
        response = client.post("/api/predict", json=payload)
        assert response.status_code == 422, f"Expected 422 when providing leakage field '{key}'"


# ---------------------------------------------------------------------------
# 3. Database Validation (404 and Missing Records)
# ---------------------------------------------------------------------------
def test_predict_unknown_supplier(valid_predict_payload):
    """Verify non-existent supplier returns HTTP 404 Not Found."""
    payload = valid_predict_payload.copy()
    payload["supplier_id"] = 999999
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 404
    assert "Supplier with ID 999999 not found" in response.json()["detail"]


def test_predict_unknown_product(valid_predict_payload):
    """Verify non-existent product returns HTTP 404 Not Found."""
    payload = valid_predict_payload.copy()
    payload["product_id"] = 999999
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 404
    assert "Product with ID 999999 not found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 4. Risk Category Threshold Boundaries
# ---------------------------------------------------------------------------
def test_risk_category_boundary_logic():
    """Verify risk categorization logic across all specified boundary values."""
    assert determine_risk_category(0.0) == "LOW"
    assert determine_risk_category(0.15) == "LOW"
    assert determine_risk_category(0.2999) == "LOW"
    assert determine_risk_category(0.30) == "MEDIUM"
    assert determine_risk_category(0.50) == "MEDIUM"
    assert determine_risk_category(0.6999) == "MEDIUM"
    assert determine_risk_category(0.70) == "HIGH"
    assert determine_risk_category(0.85) == "HIGH"
    assert determine_risk_category(1.0) == "HIGH"


def test_risk_category_custom_thresholds():
    """Verify custom risk thresholds are respected."""
    assert determine_risk_category(0.25, low_threshold=0.20, high_threshold=0.80) == "MEDIUM"
    assert determine_risk_category(0.15, low_threshold=0.20, high_threshold=0.80) == "LOW"
    assert determine_risk_category(0.85, low_threshold=0.20, high_threshold=0.80) == "HIGH"


def test_risk_tier_returned_in_api(valid_predict_payload):
    """Verify API returns the calibrated risk tier corresponding to delay_probability."""
    response = client.post("/api/predict", json=valid_predict_payload)
    assert response.status_code == 200
    data = response.json()
    prob = data["delay_probability"]
    expected_risk = determine_risk_category(prob)
    assert data["risk"] == expected_risk


# ---------------------------------------------------------------------------
# 5. Model Validation and Failure Handling (503 Service Unavailable)
# ---------------------------------------------------------------------------
def test_predict_model_artifacts_missing_503(valid_predict_payload):
    """Verify 503 Service Unavailable when model artifacts cannot be loaded."""
    with patch("app.services.prediction_service.predict_shipment", side_effect=FileNotFoundError("classifier.pkl not found")):
        response = client.post("/api/predict", json=valid_predict_payload)
        assert response.status_code == 503
        assert "Predictive ML model artifacts are unavailable" in response.json()["detail"]


def test_predict_unexpected_inference_error_500(valid_predict_payload):
    """Verify 500 Internal Server Error when unexpected runtime failure occurs."""
    with patch("app.services.prediction_service.predict_shipment", side_effect=RuntimeError("GPU OOM crash")):
        response = client.post("/api/predict", json=valid_predict_payload)
        assert response.status_code == 500
        assert "An internal error occurred while generating shipment delay prediction" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 6. Legacy Endpoint Compatibility
# ---------------------------------------------------------------------------
def test_legacy_shipment_delay_endpoint_still_functional():
    """Verify Day 7 POST /api/predictions/shipment-delay is preserved and functional."""
    payload = {
        "supplier_reliability": 0.92,
        "historical_avg_delay": 0.8,
        "lead_time": 6,
        "inventory_level": 200,
        "demand": 150,
        "quantity": 80,
        "shipping_cost": 120.0,
        "transport_mode": "Road",
        "season": "Post-Monsoon",
        "priority": "Medium",
        "distance": 350.0,
    }
    response = client.post("/api/predictions/shipment-delay", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "delayed" in data
    assert "delay_probability" in data
    assert "predicted_delay_days" in data
    assert "model_version" in data
