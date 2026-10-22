"""
SupplyPrescript — Database Write-Back & Persistence Unit Tests (Day 18)
========================================================================
Validates low-level database constraints, transactions, and ORM contracts:
- Real database INSERT creates exactly one row
- Required fields (decision_id, shipment_id, user_id, predicted_cost, predicted_delay, decision_time, status)
- Foreign key constraints (shipment_id FK rejects invalid shipments)
- Status check constraint (ck_decisions_status rejects invalid lifecycle states)
- Monetary precision preserved in NUMERIC(12, 2)
- Transaction atomicity & rollback on failure (no partial state)
- Unique idempotency key constraint rejects duplicate inserts at the database level
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy.exc import IntegrityError
from app.database.connection import SessionLocal
from app.models.decision import Decision
from app.models.recommendation import Recommendation
from app.models.shipment import Shipment


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


def test_db_insert_single_row_with_required_fields(db):
    """1. Inserting a valid decision creates exactly one row with all Day 18 fields populated."""
    shipment = db.query(Shipment).first()
    assert shipment is not None, "At least one shipment required in test database"

    rec = db.query(Recommendation).first()
    assert rec is not None, "At least one recommendation required in test database"

    unique_dec_id = f"DEC-WB-{uuid.uuid4().hex[:8].upper()}"
    now_utc = datetime.now(timezone.utc)
    cost = Decimal("41583.04")
    delay = Decimal("0.50")

    decision = Decision(
        decision_id=unique_dec_id,
        recommendation_id=rec.id,
        decision="Execute Decision: Option A (Air Freight)",
        decision_reason="Mitigates line-down delay.",
        decision_source="Optimization",
        approved_by="Lead Operations Engineer",
        status="RECORDED",
        shipment_id=shipment.shipment_id,
        strategy="AIR_FREIGHT",
        estimated_total_cost=cost,
        currency="USD",
        estimated_delivery_days=Decimal("3.50"),
        external_action_status="NOT_EXECUTED",
        user_id="usr_lead_ops",
        predicted_cost=cost,
        predicted_delay=delay,
        decision_time=now_utc,
    )

    db.add(decision)
    db.commit()
    db.refresh(decision)

    assert decision.id is not None
    assert decision.decision_id == unique_dec_id
    assert decision.shipment_id == shipment.shipment_id
    assert decision.user_id == "usr_lead_ops"
    assert decision.strategy == "AIR_FREIGHT"
    assert decision.predicted_cost == cost
    assert decision.predicted_delay == delay
    assert decision.status == "RECORDED"
    assert decision.external_action_status == "NOT_EXECUTED"
    assert decision.decision_time is not None

    # Verify directly via fresh query
    persisted = db.query(Decision).filter(Decision.decision_id == unique_dec_id).one()
    assert persisted.predicted_cost == Decimal("41583.04")
    assert persisted.predicted_delay == Decimal("0.50")

    # Clean up
    db.delete(persisted)
    db.commit()


def test_db_foreign_key_invalid_shipment_rejected(db):
    """2. Database foreign key constraint rejects non-existent shipment_id."""
    rec = db.query(Recommendation).first()
    assert rec is not None

    unique_dec_id = f"DEC-INVALID-FK-{uuid.uuid4().hex[:8].upper()}"

    invalid_decision = Decision(
        decision_id=unique_dec_id,
        recommendation_id=rec.id,
        decision="Execute Decision with Bad FK",
        decision_source="Optimization",
        status="RECORDED",
        shipment_id="NON_EXISTENT_SHIPMENT_ID_9999999",  # Does not exist in shipments
        predicted_cost=Decimal("1000.00"),
        predicted_delay=Decimal("1.00"),
        decision_time=datetime.now(timezone.utc),
    )

    db.add(invalid_decision)
    with pytest.raises(IntegrityError) as exc_info:
        db.commit()

    assert "fk_decisions_shipment_id" in str(exc_info.value).lower() or "foreign key" in str(exc_info.value).lower()
    db.rollback()


def test_db_status_check_constraint_rejects_invalid_state(db):
    """3. Check constraint ck_decisions_status rejects invalid lifecycle states."""
    rec = db.query(Recommendation).first()
    assert rec is not None

    unique_dec_id = f"DEC-BAD-STATUS-{uuid.uuid4().hex[:8].upper()}"

    invalid_decision = Decision(
        decision_id=unique_dec_id,
        recommendation_id=rec.id,
        decision="Execute Decision with Bad Status",
        decision_source="Optimization",
        status="INVALID_LIFECYCLE_STATE_XYZ",  # Not in allowed check constraint list
        predicted_cost=Decimal("1000.00"),
        predicted_delay=Decimal("1.00"),
        decision_time=datetime.now(timezone.utc),
    )

    db.add(invalid_decision)
    with pytest.raises(IntegrityError) as exc_info:
        db.commit()

    assert "ck_decisions_status" in str(exc_info.value).lower() or "check constraint" in str(exc_info.value).lower()
    db.rollback()


def test_db_monetary_precision_preserved(db):
    """4. Numeric(12, 2) preserves exact two-decimal monetary precision without float drift."""
    rec = db.query(Recommendation).first()
    assert rec is not None

    unique_dec_id = f"DEC-PRECISION-{uuid.uuid4().hex[:8].upper()}"
    exact_cost = Decimal("48765.99")

    decision = Decision(
        decision_id=unique_dec_id,
        recommendation_id=rec.id,
        decision="Precision Test",
        decision_source="Optimization",
        status="RECORDED",
        predicted_cost=exact_cost,
        estimated_total_cost=exact_cost,
        predicted_delay=Decimal("2.25"),
        decision_time=datetime.now(timezone.utc),
    )

    db.add(decision)
    db.commit()
    db.refresh(decision)

    assert decision.predicted_cost == exact_cost
    assert decision.estimated_total_cost == exact_cost

    # Clean up
    db.delete(decision)
    db.commit()


def test_db_transaction_rollback_leaves_no_partial_record(db):
    """5. An aborted database transaction completely rolls back without leaving orphan rows."""
    rec = db.query(Recommendation).first()
    assert rec is not None

    unique_dec_id = f"DEC-ROLLBACK-{uuid.uuid4().hex[:8].upper()}"

    decision = Decision(
        decision_id=unique_dec_id,
        recommendation_id=rec.id,
        decision="Rollback Test",
        decision_source="Optimization",
        status="RECORDED",
        predicted_cost=Decimal("500.00"),
        decision_time=datetime.now(timezone.utc),
    )

    db.add(decision)
    db.flush()  # Staged in transaction but not committed

    # Explicitly rollback
    db.rollback()

    # Verify row does NOT exist in database
    found = db.query(Decision).filter(Decision.decision_id == unique_dec_id).first()
    assert found is None


def test_db_idempotency_key_unique_constraint(db):
    """6. Unique index on idempotency_key prevents duplicate rows at database level."""
    rec = db.query(Recommendation).first()
    assert rec is not None

    shared_key = f"IDEMP-DB-TEST-{uuid.uuid4().hex}"

    d1 = Decision(
        decision_id=f"DEC-DUP-1-{uuid.uuid4().hex[:6]}",
        recommendation_id=rec.id,
        decision="First Insert",
        decision_source="Optimization",
        status="RECORDED",
        idempotency_key=shared_key,
        decision_time=datetime.now(timezone.utc),
    )
    db.add(d1)
    db.commit()

    # Attempt second row with same idempotency_key
    d2 = Decision(
        decision_id=f"DEC-DUP-2-{uuid.uuid4().hex[:6]}",
        recommendation_id=rec.id,
        decision="Second Duplicate Insert",
        decision_source="Optimization",
        status="RECORDED",
        idempotency_key=shared_key,
        decision_time=datetime.now(timezone.utc),
    )
    db.add(d2)
    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()

    # Clean up d1
    db.delete(d1)
    db.commit()
