"""Tests for GET /api/dashboard endpoint."""

import sys
from pathlib import Path

# Add backend directory to sys.path so app can be imported
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_dashboard_success():
    """Verify GET /api/dashboard returns 200 with aggregated metrics."""
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    res_data = response.json()
    assert "data" in res_data
    data = res_data["data"]

    # Verify key counts
    assert data["total_shipments"] == 15000
    assert data["total_suppliers"] == 50
    assert data["total_products"] == 100
    assert data["total_inventory_records"] == 20

    # Verify delayed + on_time == total_shipments
    assert data["delayed_shipments"] + data["on_time_shipments"] == data["total_shipments"]
    assert 0 <= data["delay_rate"] <= 1

    # Verify averages and costs are positive numbers
    assert data["average_delay_days"] >= 0
    assert data["average_lead_time"] > 0
    assert data["total_shipping_cost"] > 0
    assert data["average_shipping_cost"] > 0

    # Verify inventory shortage metrics
    assert data["inventory_shortage_count"] >= 0
    assert 0 <= data["inventory_shortage_rate"] <= 1

    # Verify breakdowns
    assert "shipments_by_transport_mode" in data
    assert sum(data["shipments_by_transport_mode"].values()) == data["total_shipments"]
    assert set(data["shipments_by_transport_mode"].keys()) == {"Air", "Sea", "Rail", "Road"}

    assert "shipments_by_priority" in data
    assert sum(data["shipments_by_priority"].values()) == data["total_shipments"]
    assert set(data["shipments_by_priority"].keys()) == {"Low", "Medium", "High", "Critical"}

    assert "shipments_by_delivery_status" in data
    assert data["shipments_by_delivery_status"]["on_time"] == data["on_time_shipments"]
    assert data["shipments_by_delivery_status"]["delayed"] == data["delayed_shipments"]

    # Verify top delayed suppliers list
    assert "top_delayed_suppliers" in data
    assert len(data["top_delayed_suppliers"]) <= 5
    for supplier in data["top_delayed_suppliers"]:
        assert "supplier_id" in supplier
        assert "shipment_count" in supplier
        assert "delayed_shipments" in supplier
        assert "delay_rate" in supplier
        assert supplier["shipment_count"] >= supplier["delayed_shipments"]
