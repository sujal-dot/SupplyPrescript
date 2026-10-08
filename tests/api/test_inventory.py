"""Tests for GET /api/inventory endpoint."""

import sys
from pathlib import Path

# Add backend directory to sys.path so app can be imported
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_inventory_success():
    """Verify GET /api/inventory returns 200 with default pagination."""
    response = client.get("/api/inventory")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert data["total"] == 20
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert len(data["data"]) == 20
    assert data["total_pages"] == 1

    item = data["data"][0]
    assert "product_id" in item
    assert "inventory_date" in item
    assert "inventory_level" in item
    assert "demand" in item
    assert "reorder_point" in item
    assert "safety_stock" in item
    assert "inventory_status" in item


def test_get_inventory_pagination():
    """Verify inventory pagination with custom page_size."""
    response = client.get("/api/inventory?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert len(data["data"]) == 5
    assert data["total"] == 20
    assert data["total_pages"] == 4

    response_p2 = client.get("/api/inventory?page=2&page_size=5")
    assert response_p2.status_code == 200
    data_p2 = response_p2.json()
    assert data_p2["page"] == 2
    assert len(data_p2["data"]) == 5


def test_get_inventory_filter_product_id():
    """Verify filtering inventory by product_id."""
    response = client.get("/api/inventory?product_id=PROD001")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for item in data["data"]:
        assert item["product_id"] == "PROD001"


def test_get_inventory_filter_status():
    """Verify filtering inventory by inventory_status."""
    response = client.get("/api/inventory?inventory_status=Low")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for item in data["data"]:
        assert item["inventory_status"].lower() == "low"


def test_get_inventory_invalid_pagination():
    """Verify invalid pagination triggers 422."""
    response = client.get("/api/inventory?page=0")
    assert response.status_code == 422

    response = client.get("/api/inventory?page_size=101")
    assert response.status_code == 422
