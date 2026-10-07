"""Tests for SQLAlchemy ORM relationships and end-to-end supply-chain workflow."""

import sys
from pathlib import Path
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database.connection import SessionLocal
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
    """Provides a database session for relationship testing."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_supplier_to_shipment_relationship(db_session):
    """Verify Supplier -> Shipment and Shipment -> Supplier relationship."""
    supplier = db_session.query(Supplier).join(Shipment).first()
    assert supplier is not None
    assert len(supplier.shipments) > 0

    first_shipment = supplier.shipments[0]
    assert first_shipment.supplier is not None
    assert first_shipment.supplier.supplier_id == supplier.supplier_id


def test_product_to_shipment_relationship(db_session):
    """Verify Product -> Shipment and Shipment -> Product relationship."""
    product = db_session.query(Product).join(Shipment).first()
    assert product is not None
    assert len(product.shipments) > 0

    first_shipment = product.shipments[0]
    assert first_shipment.product is not None
    assert first_shipment.product.product_id == product.product_id


def test_product_to_inventory_relationship(db_session):
    """Verify Product -> Inventory and Inventory -> Product relationship."""
    product = db_session.query(Product).join(Inventory).first()
    assert product is not None
    assert len(product.inventory) > 0

    first_inv = product.inventory[0]
    assert first_inv.product is not None
    assert first_inv.product.product_id == product.product_id


def test_shipment_to_prediction_relationship(db_session):
    """Verify Shipment -> Prediction and Prediction -> Shipment relationship."""
    prediction = db_session.query(Prediction).first()
    assert prediction is not None
    assert prediction.shipment is not None
    assert prediction.shipment.shipment_id == prediction.shipment_id
    assert prediction in prediction.shipment.predictions


def test_model_version_to_prediction_relationship(db_session):
    """Verify ModelVersion -> Prediction and Prediction -> ModelVersion relationship."""
    prediction = db_session.query(Prediction).first()
    assert prediction is not None
    assert prediction.model_version is not None
    assert prediction.model_version.id == prediction.model_version_id
    assert prediction in prediction.model_version.predictions


def test_prediction_to_recommendation_relationship(db_session):
    """Verify Prediction -> Recommendation and Recommendation -> Prediction relationship."""
    rec = db_session.query(Recommendation).first()
    assert rec is not None
    assert rec.prediction is not None
    assert rec.prediction.id == rec.prediction_id
    assert rec in rec.prediction.recommendations


def test_recommendation_to_decision_relationship(db_session):
    """Verify Recommendation -> Decision and Decision -> Recommendation relationship."""
    dec = db_session.query(Decision).first()
    assert dec is not None
    assert dec.recommendation is not None
    assert dec.recommendation.id == dec.recommendation_id
    assert dec in dec.recommendation.decisions


def test_decision_to_outcome_relationship(db_session):
    """Verify Decision -> Outcome and Outcome -> Decision relationship."""
    out = db_session.query(Outcome).first()
    assert out is not None
    assert out.decision is not None
    assert out.decision.id == out.decision_id
    assert out in out.decision.outcomes


def test_end_to_end_supply_chain_workflow_chain(db_session):
    """Test sample end-to-end workflow chain:

    Supplier -> Shipment -> Prediction -> Recommendation -> Decision -> Outcome
    Insert one complete valid chain and verify each record correctly references its parent.
    """
    prefix = "E2E_TEST_"
    s_id = f"{prefix}SUP001"
    p_id = f"{prefix}PROD001"
    sh_id = f"{prefix}SHIP000001"
    mv_name = f"{prefix}model"
    mv_ver = "v1.0"
    pr_id = f"{prefix}PRED000001"
    rc_id = f"{prefix}REC000001"
    dc_id = f"{prefix}DEC000001"
    ot_id = f"{prefix}OUT000001"

    # Clean up prior test records if any exist
    db_session.query(Outcome).filter_by(outcome_id=ot_id).delete()
    db_session.query(Decision).filter_by(decision_id=dc_id).delete()
    db_session.query(Recommendation).filter_by(recommendation_id=rc_id).delete()
    db_session.query(Prediction).filter_by(prediction_id=pr_id).delete()
    db_session.query(ModelVersion).filter_by(model_name=mv_name, version=mv_ver).delete()
    db_session.query(Shipment).filter_by(shipment_id=sh_id).delete()
    db_session.query(Supplier).filter_by(supplier_id=s_id).delete()
    db_session.query(Product).filter_by(product_id=p_id).delete()
    db_session.commit()

    try:
        # 1. Supplier
        supplier = Supplier(
            supplier_id=s_id,
            supplier_name="End-to-End Test Supplier",
            origin="Bengaluru",
            supplier_reliability=Decimal("0.9600"),
            base_lead_time=4,
            capacity=25000,
        )
        db_session.add(supplier)

        # 2. Product
        product = Product(
            product_id=p_id,
            product_name="End-to-End Test Component",
            category="Electronics",
            unit_cost=Decimal("45.50"),
            weight_kg=Decimal("1.25"),
            base_demand=Decimal("500.00"),
        )
        db_session.add(product)
        db_session.flush()

        # 3. Shipment (references Supplier and Product)
        shipment = Shipment(
            shipment_id=sh_id,
            supplier_id=supplier.supplier_id,
            product_id=product.product_id,
            origin="Bengaluru",
            destination="Delhi",
            order_date=date(2023, 5, 1),
            expected_delivery_date=date(2023, 5, 7),
            actual_delivery_date=date(2023, 5, 8),
            lead_time=6,
            quantity=250,
            unit_cost=Decimal("45.50"),
            shipping_cost=Decimal("120.00"),
            supplier_reliability=Decimal("0.9600"),
            inventory_level=600,
            demand=450,
            priority="High",
            transport_mode="Road",
            delay_days=1,
        )
        db_session.add(shipment)

        # 4. Model Version
        model_ver = ModelVersion(
            model_name=mv_name,
            version=mv_ver,
            model_type="Classification",
            algorithm="XGBoost",
            dataset_version="v1.0",
            metrics={"accuracy": 0.94, "f1": 0.92},
            is_active=True,
        )
        db_session.add(model_ver)
        db_session.flush()

        # 5. Prediction (references Shipment and ModelVersion)
        prediction = Prediction(
            prediction_id=pr_id,
            shipment_id=shipment.shipment_id,
            model_version_id=model_ver.id,
            prediction_type="Delay Risk",
            predicted_value=Decimal("1.0000"),
            prediction_probability=Decimal("0.8900"),
            prediction_status="Generated",
            prediction_horizon=7,
        )
        db_session.add(prediction)
        db_session.flush()

        # 6. Recommendation (references Prediction)
        recommendation = Recommendation(
            recommendation_id=rc_id,
            prediction_id=prediction.id,
            recommendation_type="Expedite Shipment",
            recommendation_text="High delay risk flagged. Recommend expediting via Priority Rail.",
            recommended_action="Expedite via Rail",
            priority="High",
            confidence_score=Decimal("0.8900"),
            status="Active",
        )
        db_session.add(recommendation)
        db_session.flush()

        # 7. Decision (references Recommendation)
        decision = Decision(
            decision_id=dc_id,
            recommendation_id=recommendation.id,
            decision="Approved Expedited Transport",
            decision_reason="Assembly line dependency requires on-time delivery.",
            decision_source="Human",
            approved_by="VP of Logistics",
            status="Approved",
        )
        db_session.add(decision)
        db_session.flush()

        # 8. Outcome (references Decision)
        outcome = Outcome(
            outcome_id=ot_id,
            decision_id=decision.id,
            actual_delivery_date=date(2023, 5, 7),
            actual_delay_days=0,
            actual_cost=Decimal("150.00"),
            inventory_impact=250,
            outcome_status="Success",
            success_score=Decimal("0.9800"),
            outcome_notes="Shipment arrived on time. Zero line disruptions.",
        )
        db_session.add(outcome)
        db_session.commit()

        # === Verification of complete chain ===
        # Query from Outcome all the way back to Supplier
        loaded_outcome = db_session.query(Outcome).filter_by(outcome_id=ot_id).first()
        assert loaded_outcome is not None
        assert loaded_outcome.decision_id == decision.id

        loaded_decision = loaded_outcome.decision
        assert loaded_decision.decision_id == dc_id
        assert loaded_decision.recommendation_id == recommendation.id

        loaded_rec = loaded_decision.recommendation
        assert loaded_rec.recommendation_id == rc_id
        assert loaded_rec.prediction_id == prediction.id

        loaded_pred = loaded_rec.prediction
        assert loaded_pred.prediction_id == pr_id
        assert loaded_pred.shipment_id == shipment.shipment_id
        assert loaded_pred.model_version_id == model_ver.id
        assert loaded_pred.model_version.model_name == mv_name

        loaded_shipment = loaded_pred.shipment
        assert loaded_shipment.shipment_id == sh_id
        assert loaded_shipment.supplier_id == supplier.supplier_id
        assert loaded_shipment.product_id == product.product_id

        loaded_supplier = loaded_shipment.supplier
        assert loaded_supplier.supplier_id == s_id
        assert loaded_supplier.supplier_name == "End-to-End Test Supplier"

        loaded_product = loaded_shipment.product
        assert loaded_product.product_id == p_id
        assert loaded_product.product_name == "End-to-End Test Component"

        # Also verify forward navigation from Supplier down to Outcome
        assert loaded_shipment in loaded_supplier.shipments
        assert loaded_pred in loaded_shipment.predictions
        assert loaded_rec in loaded_pred.recommendations
        assert loaded_decision in loaded_rec.decisions
        assert loaded_outcome in loaded_decision.outcomes

    finally:
        # Clean up
        db_session.query(Outcome).filter_by(outcome_id=ot_id).delete()
        db_session.query(Decision).filter_by(decision_id=dc_id).delete()
        db_session.query(Recommendation).filter_by(recommendation_id=rc_id).delete()
        db_session.query(Prediction).filter_by(prediction_id=pr_id).delete()
        db_session.query(ModelVersion).filter_by(model_name=mv_name, version=mv_ver).delete()
        db_session.query(Shipment).filter_by(shipment_id=sh_id).delete()
        db_session.query(Supplier).filter_by(supplier_id=s_id).delete()
        db_session.query(Product).filter_by(product_id=p_id).delete()
        db_session.commit()
