"""Tests for PostgreSQL database schema, tables, constraints, and indexes."""

import sys
from pathlib import Path
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database.connection import engine, SessionLocal
from app.models import (
    Supplier,
    Product,
    Shipment,
    Inventory,
    ModelVersion,
    Prediction,
    Recommendation,
    Decision,
    Outcome,
)


@pytest.fixture
def db_session():
    """Provides a transactional database session for testing."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_all_nine_tables_exist():
    """Verify all 9 required tables exist in PostgreSQL schema."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    required_tables = {
        "suppliers",
        "products",
        "shipments",
        "inventory",
        "model_versions",
        "predictions",
        "recommendations",
        "decisions",
        "outcomes",
    }

    missing_tables = required_tables - existing_tables
    assert not missing_tables, f"Missing tables in database: {missing_tables}"


def test_unique_supplier_id_constraint(db_session):
    """Test that duplicate supplier_id raises an IntegrityError."""
    test_id = "TEST_SUP_UNIQUE_01"
    # Clean up prior if exists
    db_session.query(Supplier).filter_by(supplier_id=test_id).delete()
    db_session.commit()

    s1 = Supplier(
        supplier_id=test_id,
        supplier_name="Test Supplier 1",
        origin="Bengaluru",
        supplier_reliability=Decimal("0.9500"),
    )
    db_session.add(s1)
    db_session.commit()

    s2 = Supplier(
        supplier_id=test_id,
        supplier_name="Test Supplier 2 Duplicate",
        origin="Pune",
        supplier_reliability=Decimal("0.9000"),
    )
    db_session.add(s2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Clean up
    db_session.query(Supplier).filter_by(supplier_id=test_id).delete()
    db_session.commit()


def test_unique_product_id_constraint(db_session):
    """Test that duplicate product_id raises an IntegrityError."""
    test_id = "TEST_PROD_UNIQUE_01"
    db_session.query(Product).filter_by(product_id=test_id).delete()
    db_session.commit()

    p1 = Product(
        product_id=test_id,
        product_name="Product 1",
        category="Test",
        unit_cost=Decimal("10.00"),
        weight_kg=Decimal("1.50"),
        base_demand=Decimal("100.00"),
    )
    db_session.add(p1)
    db_session.commit()

    p2 = Product(
        product_id=test_id,
        product_name="Product 2 Duplicate",
        category="Test",
        unit_cost=Decimal("20.00"),
        weight_kg=Decimal("2.50"),
        base_demand=Decimal("200.00"),
    )
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Clean up
    db_session.query(Product).filter_by(product_id=test_id).delete()
    db_session.commit()


def test_unique_shipment_id_constraint(db_session):
    """Test that duplicate shipment_id raises an IntegrityError."""
    test_id = "TEST_SHIP_UNIQUE_01"
    sup = db_session.query(Supplier).first()
    prod = db_session.query(Product).first()
    assert sup is not None and prod is not None

    db_session.query(Shipment).filter_by(shipment_id=test_id).delete()
    db_session.commit()

    s1 = Shipment(
        shipment_id=test_id,
        supplier_id=sup.supplier_id,
        product_id=prod.product_id,
        origin="Bengaluru",
        destination="Delhi",
        order_date=date(2023, 1, 1),
        expected_delivery_date=date(2023, 1, 7),
        actual_delivery_date=date(2023, 1, 7),
        lead_time=6,
        quantity=100,
        unit_cost=Decimal("25.00"),
        shipping_cost=Decimal("50.00"),
        supplier_reliability=Decimal("0.9500"),
        inventory_level=500,
        demand=200,
        priority="Medium",
        transport_mode="Road",
        delay_days=0,
    )
    db_session.add(s1)
    db_session.commit()

    s2 = Shipment(
        shipment_id=test_id,
        supplier_id=sup.supplier_id,
        product_id=prod.product_id,
        origin="Bengaluru",
        destination="Delhi",
        order_date=date(2023, 1, 1),
        expected_delivery_date=date(2023, 1, 7),
        actual_delivery_date=date(2023, 1, 7),
        lead_time=6,
        quantity=100,
        unit_cost=Decimal("25.00"),
        shipping_cost=Decimal("50.00"),
        supplier_reliability=Decimal("0.9500"),
        inventory_level=500,
        demand=200,
        priority="Medium",
        transport_mode="Road",
        delay_days=0,
    )
    db_session.add(s2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Clean up
    db_session.query(Shipment).filter_by(shipment_id=test_id).delete()
    db_session.commit()


def test_unique_model_name_and_version_constraint(db_session):
    """Test that duplicate (model_name, version) raises an IntegrityError."""
    m_name = "test_model_unique"
    m_ver = "v9.9.9"

    db_session.query(ModelVersion).filter_by(model_name=m_name, version=m_ver).delete()
    db_session.commit()

    mv1 = ModelVersion(
        model_name=m_name,
        version=m_ver,
        model_type="Classification",
        algorithm="XGBoost",
    )
    db_session.add(mv1)
    db_session.commit()

    mv2 = ModelVersion(
        model_name=m_name,
        version=m_ver,
        model_type="Classification",
        algorithm="RandomForest",
    )
    db_session.add(mv2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Clean up
    db_session.query(ModelVersion).filter_by(model_name=m_name, version=m_ver).delete()
    db_session.commit()


def test_supplier_reliability_check_constraint(db_session):
    """Test supplier reliability must be between 0 and 1."""
    invalid_supplier = Supplier(
        supplier_id="TEST_SUP_INVALID_REL",
        supplier_name="Invalid Supplier",
        origin="Bengaluru",
        supplier_reliability=Decimal("1.5000"),  # > 1.0 violates check constraint
    )
    db_session.add(invalid_supplier)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_shipment_quantity_check_constraint(db_session):
    """Test shipment quantity must be strictly greater than 0."""
    sup = db_session.query(Supplier).first()
    prod = db_session.query(Product).first()

    invalid_shipment = Shipment(
        shipment_id="TEST_SHIP_INVALID_QTY",
        supplier_id=sup.supplier_id,
        product_id=prod.product_id,
        origin="Bengaluru",
        destination="Delhi",
        order_date=date(2023, 1, 1),
        expected_delivery_date=date(2023, 1, 7),
        actual_delivery_date=date(2023, 1, 7),
        lead_time=6,
        quantity=0,  # <= 0 violates check constraint
        unit_cost=Decimal("25.00"),
        shipping_cost=Decimal("50.00"),
        supplier_reliability=Decimal("0.9500"),
        inventory_level=500,
        demand=200,
        priority="Medium",
        transport_mode="Road",
        delay_days=0,
    )
    db_session.add(invalid_shipment)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_shipment_delay_days_check_constraint(db_session):
    """Test delay_days cannot be negative."""
    sup = db_session.query(Supplier).first()
    prod = db_session.query(Product).first()

    invalid_shipment = Shipment(
        shipment_id="TEST_SHIP_INVALID_DELAY",
        supplier_id=sup.supplier_id,
        product_id=prod.product_id,
        origin="Bengaluru",
        destination="Delhi",
        order_date=date(2023, 1, 1),
        expected_delivery_date=date(2023, 1, 7),
        actual_delivery_date=date(2023, 1, 7),
        lead_time=6,
        quantity=100,
        unit_cost=Decimal("25.00"),
        shipping_cost=Decimal("50.00"),
        supplier_reliability=Decimal("0.9500"),
        inventory_level=500,
        demand=200,
        priority="Medium",
        transport_mode="Road",
        delay_days=-5,  # < 0 violates check constraint
    )
    db_session.add(invalid_shipment)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_outcome_success_score_check_constraint(db_session):
    """Test outcome success_score must be between 0 and 1."""
    dec = db_session.query(Decision).first()
    assert dec is not None

    invalid_outcome = Outcome(
        outcome_id="TEST_OUT_INVALID_SCORE",
        decision_id=dec.id,
        actual_delay_days=0,
        actual_cost=Decimal("100.00"),
        outcome_status="Success",
        success_score=Decimal("1.5000"),  # > 1.0 violates check constraint
    )
    db_session.add(invalid_outcome)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_restrict_foreign_key_deletion_behavior(db_session):
    """Test that deleting a supplier with existing shipments is RESTRICTED."""
    sup = db_session.query(Supplier).join(Shipment).first()
    assert sup is not None

    db_session.delete(sup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
