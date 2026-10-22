"""SupplyPrescript — Database Unit Tests for Decision Outcomes (Day 19)
======================================================================
Tests verify that operational actual outcomes are committed to the PostgreSQL
database table 'outcomes' with schema integrity, unique one-to-one constraint,
check constraints, and relational consistency.
"""

import sys
from pathlib import Path
from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy.exc import IntegrityError

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database.connection import SessionLocal
from app.models.decision import Decision
from app.models.outcome import Outcome
from app.models.shipment import Shipment


@pytest.fixture
def db_session():
    """Provides a transactional database session for testing."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_real_sql_insert_and_commit_outcome(db_session):
    """Verify an outcome row is genuinely committed to PostgreSQL and re-read."""
    # Find an existing decision that does not yet have an outcome
    existing_outcomes_dec_ids = {o.decision_id for o in db_session.query(Outcome.decision_id).all()}
    decision = (
        db_session.query(Decision)
        .filter(~Decision.id.in_(existing_outcomes_dec_ids))
        .first()
    )
    assert decision is not None, "A test decision must exist"

    test_outcome_id = f"TEST-OUT-{uuid.uuid4().hex[:8].upper()}"
    outcome = Outcome(
        outcome_id=test_outcome_id,
        decision_id=decision.id,
        decision_business_id=decision.decision_id,
        shipment_id=decision.shipment_id,
        actual_cost=Decimal("15450.75"),
        currency="USD",
        actual_delivery_date=date(2026, 10, 25),
        actual_delay=Decimal("1.50"),
        actual_delay_days=1,
        baseline_delivery_date=date(2026, 10, 24),
        actual_supplier="SUPPLIER_TEST_ACTUAL",
        actual_quantity=Decimal("1200.00"),
        outcome_status="DELIVERED",
        source="manual_entry",
        notes="Real outcome persisted to PostgreSQL.",
        recorded_by="usr_test_lead",
    )

    try:
        db_session.add(outcome)
        db_session.commit()

        # Re-fetch in a fresh query
        saved = db_session.query(Outcome).filter_by(outcome_id=test_outcome_id).first()
        assert saved is not None
        assert saved.decision_id == decision.id
        assert saved.decision_business_id == decision.decision_id
        assert saved.actual_cost == Decimal("15450.75")
        assert saved.actual_delay == Decimal("1.50")
        assert saved.outcome_status == "DELIVERED"
        assert saved.recorded_by == "usr_test_lead"
        assert saved.decision is not None
        assert saved.decision.id == decision.id
    finally:
        db_session.query(Outcome).filter_by(outcome_id=test_outcome_id).delete()
        db_session.commit()


def test_unique_decision_id_one_to_one_constraint(db_session):
    """Verify that a decision cannot have two recorded outcomes (uq_outcomes_decision_id)."""
    existing_outcomes_dec_ids = {o.decision_id for o in db_session.query(Outcome.decision_id).all()}
    decision = (
        db_session.query(Decision)
        .filter(~Decision.id.in_(existing_outcomes_dec_ids))
        .first()
    )
    assert decision is not None

    out1_id = f"TEST-OUT-UQ1-{uuid.uuid4().hex[:6]}"
    out2_id = f"TEST-OUT-UQ2-{uuid.uuid4().hex[:6]}"

    out1 = Outcome(
        outcome_id=out1_id,
        decision_id=decision.id,
        actual_cost=Decimal("1000.00"),
        outcome_status="RECORDED",
    )
    db_session.add(out1)
    db_session.commit()

    try:
        out2 = Outcome(
            outcome_id=out2_id,
            decision_id=decision.id,  # Duplicate decision_id
            actual_cost=Decimal("2000.00"),
            outcome_status="RECORDED",
        )
        db_session.add(out2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
    finally:
        db_session.query(Outcome).filter_by(outcome_id=out1_id).delete()
        db_session.commit()


def test_check_constraint_negative_actual_cost(db_session):
    """Verify check constraint ck_outcomes_actual_cost rejects negative actual cost."""
    existing_outcomes_dec_ids = {o.decision_id for o in db_session.query(Outcome.decision_id).all()}
    decision = db_session.query(Decision).filter(~Decision.id.in_(existing_outcomes_dec_ids)).first()
    assert decision is not None

    invalid_out = Outcome(
        outcome_id=f"TEST-OUT-NEG-{uuid.uuid4().hex[:6]}",
        decision_id=decision.id,
        actual_cost=Decimal("-500.00"),  # Violates ck_outcomes_actual_cost
        outcome_status="RECORDED",
    )
    db_session.add(invalid_out)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_check_constraint_negative_actual_delay(db_session):
    """Verify check constraint ck_outcomes_actual_delay rejects negative actual delay."""
    existing_outcomes_dec_ids = {o.decision_id for o in db_session.query(Outcome.decision_id).all()}
    decision = db_session.query(Decision).filter(~Decision.id.in_(existing_outcomes_dec_ids)).first()
    assert decision is not None

    invalid_out = Outcome(
        outcome_id=f"TEST-OUT-NEGDELAY-{uuid.uuid4().hex[:6]}",
        decision_id=decision.id,
        actual_cost=Decimal("1000.00"),
        actual_delay=Decimal("-2.50"),  # Violates ck_outcomes_actual_delay
        outcome_status="RECORDED",
    )
    db_session.add(invalid_out)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_monetary_precision_numeric_scale(db_session):
    """Verify precision and two decimal scale storage for actual_cost."""
    existing_outcomes_dec_ids = {o.decision_id for o in db_session.query(Outcome.decision_id).all()}
    decision = db_session.query(Decision).filter(~Decision.id.in_(existing_outcomes_dec_ids)).first()
    assert decision is not None

    test_id = f"TEST-OUT-PREC-{uuid.uuid4().hex[:6]}"
    precise_cost = Decimal("98765.43")
    out = Outcome(
        outcome_id=test_id,
        decision_id=decision.id,
        actual_cost=precise_cost,
        actual_delay=Decimal("3.75"),
        outcome_status="DELIVERED",
    )
    try:
        db_session.add(out)
        db_session.commit()

        reloaded = db_session.query(Outcome).filter_by(outcome_id=test_id).first()
        assert reloaded.actual_cost == precise_cost
        assert reloaded.actual_delay == Decimal("3.75")
    finally:
        db_session.query(Outcome).filter_by(outcome_id=test_id).delete()
        db_session.commit()
