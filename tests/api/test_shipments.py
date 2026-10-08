"""Tests for GET /api/shipments endpoint."""

import sys
from pathlib import Path

# Add backend directory to sys.path so app can be imported
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_shipments_success():
    """Verify GET /api/shipments returns 200 with default pagination."""
    response = client.get("/api/shipments")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert data["total"] == 15000
    assert data["page"] == 1
    assert data["page_size"] == 50
    assert len(data["data"]) == 50
    assert data["total_pages"] == 300

    item = data["data"][0]
    assert "shipment_id" in item
    assert "supplier_id" in item
    assert "product_id" in item
    assert "origin" in item
    assert "destination" in item
    assert "order_date" in item
    assert "expected_delivery_date" in item
    assert "actual_delivery_date" in item
    assert "lead_time" in item
    assert "quantity" in item
    assert "unit_cost" in item
    assert "shipping_cost" in item
    assert "supplier_reliability" in item
    assert "inventory_level" in item
    assert "demand" in item
    assert "priority" in item
    assert "transport_mode" in item
    assert "delay_days" in item


def test_get_shipments_pagination():
    """Verify custom page and page_size works correctly."""
    response = client.get("/api/shipments?page=2&page_size=25")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 25
    assert len(data["data"]) == 25


def test_get_shipments_filter_supplier_id():
    """Verify filtering by supplier_id."""
    response = client.get("/api/shipments?supplier_id=SUP001")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for s in data["data"]:
        assert s["supplier_id"] == "SUP001"


def test_get_shipments_filter_product_id():
    """Verify filtering by product_id."""
    response = client.get("/api/shipments?product_id=PROD001")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for s in data["data"]:
        assert s["product_id"] == "PROD001"


def test_get_shipments_filter_priority():
    """Verify filtering by priority."""
    response = client.get("/api/shipments?priority=Critical")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for s in data["data"]:
        assert s["priority"].lower() == "critical"


def test_get_shipments_filter_transport_mode():
    """Verify filtering by transport_mode."""
    response = client.get("/api/shipments?transport_mode=Air")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for s in data["data"]:
        assert s["transport_mode"].lower() == "air"


def test_get_shipments_filter_is_delayed():
    """Verify filtering by is_delayed flag."""
    response = client.get("/api/shipments?is_delayed=true")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for s in data["data"]:
        assert s["delay_days"] > 0

    response_ontime = client.get("/api/shipments?is_delayed=false")
    assert response_ontime.status_code == 200
    data_ontime = response_ontime.json()
    assert data_ontime["total"] > 0
    for s in data_ontime["data"]:
        assert s["delay_days"] == 0


def test_get_shipments_date_range_filter():
    """Verify filtering by start_date and end_date."""
    response = client.get("/api/shipments?start_date=2023-01-01&end_date=2023-01-31")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for s in data["data"]:
        assert "2023-01-01" <= s["order_date"] <= "2023-01-31"


def test_get_shipments_invalid_date_range():
    """Verify start_date > end_date returns 400."""
    response = client.get("/api/shipments?start_date=2023-06-01&end_date=2023-01-01")
    assert response.status_code == 400
    assert "start_date must be less than or equal to end_date" in response.json()["detail"]


def test_get_shipments_sorting():
    """Verify sorting by allowed fields."""
    response = client.get("/api/shipments?sort_by=quantity&sort_order=desc&page_size=10")
    assert response.status_code == 200
    data = response.json()
    quantities = [item["quantity"] for item in data["data"]]
    assert quantities == sorted(quantities, reverse=True)

    response_delay = client.get("/api/shipments?sort_by=delay_days&sort_order=desc&page_size=10")
    assert response_delay.status_code == 200
    delays = [item["delay_days"] for item in response_delay.json()["data"]]
    assert delays == sorted(delays, reverse=True)


def test_get_shipments_invalid_sorting():
    """Verify invalid sort field returns 400."""
    response = client.get("/api/shipments?sort_by=invalid_field")
    assert response.status_code == 400

    response_order = client.get("/api/shipments?sort_order=sideways")
    assert response_order.status_code == 400


def test_get_shipments_combined_filters():
    """Verify combining multiple filters together."""
    response = client.get(
        "/api/shipments?transport_mode=Road&priority=High&is_delayed=true&page_size=10"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for s in data["data"]:
        assert s["transport_mode"].lower() == "road"
        assert s["priority"].lower() == "high"
        assert s["delay_days"] > 0
