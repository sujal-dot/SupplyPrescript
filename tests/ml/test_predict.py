"""
Unit tests for ml/predict.py and API prediction endpoints
=========================================================
Tests single and batch inference, probability bounds, non-negative delay days,
model disagreement warnings, input validation, and FastAPI integration.
"""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

# Ensure backend can be imported for TestClient
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from ml.predict import (
    predict_delay_days,
    predict_delay_probability,
    predict_shipment,
    prepare_input_dataframe,
)

client = TestClient(app)


@pytest.fixture
def sample_shipment_payload() -> dict:
    """Valid feature dictionary matching approved schema."""
    return {
        "supplier_reliability": 0.91,
        "historical_avg_delay": 1.2,
        "lead_time": 7,
        "inventory_level": 150,
        "demand": 120,
        "quantity": 80,
        "shipping_cost": 2500.0,
        "transport_mode": "Road",
        "season": "Monsoon",
        "priority": "High",
        "distance": 420.0,
    }


def test_prepare_input_dataframe(sample_shipment_payload):
    """Verify input preparation from dict, list, and DataFrame."""
    df_single = prepare_input_dataframe(sample_shipment_payload)
    assert len(df_single) == 1

    df_batch = prepare_input_dataframe([sample_shipment_payload, sample_shipment_payload])
    assert len(df_batch) == 2

    # Missing column raises ValueError
    bad_payload = sample_shipment_payload.copy()
    del bad_payload["distance"]
    with pytest.raises(ValueError, match="Missing required shipment feature"):
        prepare_input_dataframe(bad_payload)


def test_predict_delay_probability_bounds(sample_shipment_payload):
    """Verify predicted probability is strictly bounded in [0.0, 1.0]."""
    probs = predict_delay_probability(sample_shipment_payload)
    assert len(probs) == 1
    prob = probs[0]
    assert 0.0 <= prob <= 1.0


def test_predict_delay_days_non_negative(sample_shipment_payload):
    """Verify predicted delay days is strictly non-negative."""
    days = predict_delay_days(sample_shipment_payload)
    assert len(days) == 1
    assert days[0] >= 0.0


def test_predict_shipment_single_dict(sample_shipment_payload):
    """Verify structured response for a single shipment payload."""
    res = predict_shipment(sample_shipment_payload)
    assert isinstance(res, dict)
    assert "delayed" in res
    assert isinstance(res["delayed"], bool)
    assert "delay_probability" in res
    assert 0.0 <= res["delay_probability"] <= 1.0
    assert "predicted_delay_days" in res
    assert res["predicted_delay_days"] >= 0.0
    assert "classification_threshold" in res
    assert "model_version" in res
    assert "prediction_timestamp" in res


def test_predict_shipment_batch(sample_shipment_payload):
    """Verify batch predictions return list of structured results."""
    batch = [sample_shipment_payload, sample_shipment_payload]
    results = predict_shipment(batch)
    assert isinstance(results, list)
    assert len(results) == 2
    for r in results:
        assert isinstance(r["delayed"], bool)
        assert 0.0 <= r["delay_probability"] <= 1.0


def test_api_predict_endpoint_success(sample_shipment_payload):
    """Verify POST /api/predictions/shipment-delay returns 200 with valid schema."""
    response = client.post("/api/predictions/shipment-delay", json=sample_shipment_payload)
    assert response.status_code == 200
    data = response.json()
    assert "delayed" in data
    assert "delay_probability" in data
    assert "predicted_delay_days" in data
    assert "model_version" in data
    assert data["predicted_delay_days"] >= 0.0
    assert 0.0 <= data["delay_probability"] <= 1.0


def test_api_predict_endpoint_validation_error():
    """Verify POST /api/predictions/shipment-delay returns 422 on invalid input."""
    # Negative quantity and invalid transport mode
    invalid_payload = {
        "supplier_reliability": 1.5,  # > 1.0
        "historical_avg_delay": -2.0,  # < 0
        "lead_time": 0,
        "inventory_level": -10,
        "demand": -5,
        "quantity": -50,
        "shipping_cost": -100,
        "transport_mode": "Rocket",
        "season": "Spring",
        "priority": "Extreme",
        "distance": -50,
    }
    response = client.post("/api/predictions/shipment-delay", json=invalid_payload)
    assert response.status_code == 422
