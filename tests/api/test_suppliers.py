"""Tests for GET /api/suppliers endpoint."""

import sys
from pathlib import Path

# Add backend directory to sys.path so app can be imported
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_suppliers_success():
    """Verify GET /api/suppliers returns 200 with default pagination."""
    response = client.get("/api/suppliers")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert data["total"] == 50
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert len(data["data"]) == 20
    assert data["total_pages"] == 3

    # Check structure of a supplier record
    item = data["data"][0]
    assert "supplier_id" in item
    assert "supplier_name" in item
    assert "origin" in item
    assert "supplier_reliability" in item


def test_get_suppliers_pagination():
    """Verify custom page and page_size works correctly."""
    response = client.get("/api/suppliers?page=2&page_size=15")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 15
    assert len(data["data"]) == 15
    assert data["total"] == 50
    assert data["total_pages"] == 4


def test_get_suppliers_filter_by_origin():
    """Verify filtering suppliers by origin city."""
    response = client.get("/api/suppliers?origin=Mumbai")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for supplier in data["data"]:
        assert supplier["origin"].lower() == "mumbai"


def test_get_suppliers_filter_by_reliability():
    """Verify filtering suppliers by minimum reliability."""
    response = client.get("/api/suppliers?min_reliability=0.95")
    assert response.status_code == 200
    data = response.json()
    for supplier in data["data"]:
        assert float(supplier["supplier_reliability"]) >= 0.95


def test_get_suppliers_filter_combined():
    """Verify combining origin and minimum reliability filters."""
    response = client.get("/api/suppliers?origin=Mumbai&min_reliability=0.85")
    assert response.status_code == 200
    data = response.json()
    for supplier in data["data"]:
        assert supplier["origin"].lower() == "mumbai"
        assert float(supplier["supplier_reliability"]) >= 0.85


def test_get_suppliers_invalid_pagination():
    """Verify invalid pagination parameters return 422 validation errors."""
    # page < 1
    response = client.get("/api/suppliers?page=0")
    assert response.status_code == 422

    # page_size > 100
    response = client.get("/api/suppliers?page_size=101")
    assert response.status_code == 422

    # page_size < 1
    response = client.get("/api/suppliers?page_size=0")
    assert response.status_code == 422
