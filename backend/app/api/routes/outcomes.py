"""SupplyPrescript — Outcomes API Router (Day 19 Closed-Loop)
=============================================================
Endpoints for listing, filtering, and retrieving operational outcome records
persisted in PostgreSQL.
"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, desc
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.outcome import Outcome
from app.models.decision import Decision
from app.models.shipment import Shipment
from app.schemas.outcome import (
    OutcomeListResponse,
    OutcomeRecordResponse,
    OutcomeComparisonResponse,
)
from app.services.outcome_comparison import compute_outcome_comparison

router = APIRouter(prefix="/api/outcomes", tags=["Outcomes"])


@router.get(
    "",
    response_model=OutcomeListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Operational Outcomes with Pagination & Filtering (Day 19)",
    description=(
        "Retrieves a paginated list of recorded operational outcomes. Supports filtering by "
        "shipment ID, fulfilling supplier, outcome status, and delivery date range."
    ),
)
def list_outcomes_endpoint(
    shipment_id: Optional[str] = Query(None, description="Filter by shipment ID"),
    supplier: Optional[str] = Query(None, description="Filter by fulfilling supplier ID"),
    outcome_status: Optional[str] = Query(None, description="Filter by outcome lifecycle status"),
    start_date: Optional[date] = Query(None, description="Filter by actual delivery date >= start_date"),
    end_date: Optional[date] = Query(None, description="Filter by actual delivery date <= end_date"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records per page"),
    offset: int = Query(0, ge=0, description="Zero-based record offset"),
    db: Session = Depends(get_db),
) -> OutcomeListResponse:
    """GET /api/outcomes handler."""
    query = db.query(Outcome)

    if shipment_id:
        clean_shipment = shipment_id.strip()
        query = query.filter(Outcome.shipment_id == clean_shipment)

    if supplier:
        clean_supplier = supplier.strip()
        query = query.filter(Outcome.actual_supplier.ilike(f"%{clean_supplier}%"))

    if outcome_status:
        clean_status = outcome_status.strip()
        query = query.filter(Outcome.outcome_status.ilike(clean_status))

    if start_date:
        query = query.filter(Outcome.actual_delivery_date >= start_date)

    if end_date:
        query = query.filter(Outcome.actual_delivery_date <= end_date)

    total = query.count()
    records = query.order_by(desc(Outcome.recorded_at)).offset(offset).limit(limit).all()

    items = []
    for rec in records:
        dec_id = rec.decision_business_id
        if not dec_id and rec.decision:
            dec_id = rec.decision.decision_id
        if not dec_id:
            dec_id = str(rec.decision_id)

        items.append(
            OutcomeRecordResponse(
                outcome_id=rec.outcome_id,
                decision_id=dec_id,
                shipment_id=rec.shipment_id,
                actual_cost=rec.actual_cost,
                currency=rec.currency or "USD",
                actual_delivery_date=rec.actual_delivery_date,
                actual_delay=rec.actual_delay,
                baseline_delivery_date=rec.baseline_delivery_date,
                actual_supplier=rec.actual_supplier,
                actual_quantity=rec.actual_quantity,
                outcome_status=rec.outcome_status,
                source=rec.source or "manual_entry",
                notes=rec.notes,
                recorded_by=rec.recorded_by,
                recorded_at=rec.recorded_at,
                updated_at=rec.updated_at,
            )
        )

    return OutcomeListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.get(
    "/{outcome_id}",
    response_model=OutcomeComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Outcome & Closed-Loop Comparison by Outcome ID (Day 19)",
)
def get_outcome_by_id_endpoint(
    outcome_id: str,
    db: Session = Depends(get_db),
) -> OutcomeComparisonResponse:
    """GET /api/outcomes/{outcome_id} handler."""
    clean_id = outcome_id.strip()
    outcome = (
        db.query(Outcome)
        .filter(or_(Outcome.outcome_id == clean_id, Outcome.id == int(clean_id) if clean_id.isdigit() else False))
        .first()
    )
    if not outcome:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Outcome record '{clean_id}' was not found.",
        )

    decision = outcome.decision
    if not decision and outcome.decision_id:
        decision = db.query(Decision).filter(Decision.id == outcome.decision_id).first()

    shipment = outcome.shipment
    if not shipment and outcome.shipment_id:
        shipment = db.query(Shipment).filter(Shipment.shipment_id == outcome.shipment_id).first()

    comparison = compute_outcome_comparison(
        decision=decision,
        outcome=outcome,
        shipment=shipment,
    )

    dec_id = getattr(outcome, "decision_business_id", None) or (decision.decision_id if decision else str(outcome.decision_id))
    comparison["outcome"] = OutcomeRecordResponse(
        outcome_id=outcome.outcome_id,
        decision_id=dec_id,
        shipment_id=outcome.shipment_id,
        actual_cost=outcome.actual_cost,
        currency=outcome.currency or "USD",
        actual_delivery_date=outcome.actual_delivery_date,
        actual_delay=outcome.actual_delay,
        baseline_delivery_date=outcome.baseline_delivery_date,
        actual_supplier=outcome.actual_supplier,
        actual_quantity=outcome.actual_quantity,
        outcome_status=outcome.outcome_status,
        source=outcome.source or "manual_entry",
        notes=outcome.notes,
        recorded_by=outcome.recorded_by,
        recorded_at=outcome.recorded_at,
        updated_at=outcome.updated_at,
    )

    return OutcomeComparisonResponse(**comparison)
