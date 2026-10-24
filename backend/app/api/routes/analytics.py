"""SupplyPrescript — Analytics API Router (Day 20/21 Decision ROI Engine & Dashboard)
==================================================================================
Portfolio-level closed-loop ROI analytics, aggregate decision performance summaries,
and multi-dimensional closed-loop dashboard intelligence.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_, desc
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.decision import Decision
from app.models.outcome import Outcome
from app.models.shipment import Shipment
from app.schemas.roi import DecisionROIDashboardResponse, PortfolioROISummaryResponse, DecisionROIResponse
from app.services.decision_roi import calculate_decision_roi, compute_portfolio_roi, compute_decision_roi_dashboard

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get(
    "/decision-roi",
    response_model=DecisionROIDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Portfolio-Level Decision ROI & Dashboard Analytics (Day 21)",
    description=(
        "Calculates aggregated decision ROI metrics and multi-dimensional analytics across authorized "
        "decisions and recorded outcomes in PostgreSQL. Returns summary KPIs, prediction accuracy metrics, "
        "success vs failure breakdown, strategy cost differences, savings timelines, and paginated decision "
        "audit records. Isolates currencies and strictly adheres to non-distorting statistical denominators."
    ),
)
def get_portfolio_decision_roi_endpoint(
    shipment_id: Optional[str] = Query(None, description="Filter portfolio decisions by shipment ID"),
    strategy: Optional[str] = Query(None, description="Filter by operational strategy (e.g. AIR_FREIGHT, SECONDARY_SUPPLIER)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by decision operational status (e.g. RECORDED, Pending)"),
    decision_status: Optional[str] = Query(None, description="Filter by operational or evaluation status (e.g. SUCCESS, FAILURE, RECORDED)"),
    supplier: Optional[str] = Query(None, description="Filter by fulfilling or assigned supplier ID"),
    start_date: Optional[datetime] = Query(None, description="Decisions created on or after this timestamp"),
    end_date: Optional[datetime] = Query(None, description="Decisions created on or before this timestamp"),
    currency: str = Query("USD", description="Currency filter for financial comparability"),
    page: int = Query(1, ge=1, description="Page number for paginated decision performance table"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page for decision performance table"),
    db: Session = Depends(get_db),
) -> DecisionROIDashboardResponse:
    """GET /api/analytics/decision-roi handler with full Day 21 dashboard intelligence."""
    query = db.query(Decision)

    if shipment_id:
        clean_shipment = shipment_id.strip()
        query = query.filter(Decision.shipment_id.ilike(f"%{clean_shipment}%"))

    if strategy:
        clean_strat = strategy.strip()
        query = query.filter(Decision.strategy.ilike(f"%{clean_strat}%"))

    effective_status = decision_status or status_filter
    eval_filter_target = None
    if effective_status:
        clean_stat = effective_status.strip().upper()
        if clean_stat in ("SUCCESS", "PARTIAL_SUCCESS", "FAILURE", "PENDING_REVIEW"):
            eval_filter_target = clean_stat
        else:
            query = query.filter(Decision.status.ilike(effective_status.strip()))

    if start_date:
        query = query.filter(Decision.decision_time >= start_date)

    if end_date:
        query = query.filter(Decision.decision_time <= end_date)

    # Order by decision_time desc, id desc
    decisions = query.order_by(desc(Decision.decision_time), desc(Decision.id)).all()

    # Pre-fetch outcomes and shipments
    decision_roi_items: List[dict] = []
    for dec in decisions:
        outcome = (
            db.query(Outcome)
            .filter(Outcome.decision_id == dec.id)
            .first()
        )

        shipment = None
        if dec.shipment_id:
            shipment = (
                db.query(Shipment)
                .filter(Shipment.shipment_id == dec.shipment_id)
                .first()
            )

        # Supplier filter
        if supplier:
            clean_sup = supplier.strip().upper()
            act_sup = getattr(outcome, "actual_supplier", None) if outcome else None
            plan_sup = getattr(shipment, "supplier_id", None) if shipment else None
            match_act = act_sup and clean_sup in act_sup.upper()
            match_plan = plan_sup and clean_sup in plan_sup.upper()
            if not (match_act or match_plan):
                continue

        roi_data = calculate_decision_roi(
            decision=dec,
            outcome=outcome,
            shipment=shipment,
        )

        # Attach decision metadata for table and timeline
        roi_data["db_id"] = dec.id
        roi_data["strategy"] = dec.strategy
        roi_data["decision_name"] = dec.decision
        roi_data["decision_time"] = dec.decision_time or dec.created_at
        roi_data["status"] = dec.status

        # If evaluation status filter active, filter here
        if eval_filter_target:
            actual_eval = roi_data.get("decision_evaluation", {}).get("decision_success")
            if actual_eval != eval_filter_target:
                continue

        decision_roi_items.append(roi_data)

    active_filters: Dict[str, Any] = {
        "shipment_id": shipment_id,
        "strategy": strategy,
        "decision_status": effective_status,
        "supplier": supplier,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "currency": currency.upper(),
        "page": page,
        "page_size": page_size,
    }

    dashboard_data = compute_decision_roi_dashboard(
        evaluated_records=decision_roi_items,
        target_currency=currency.upper(),
        page=page,
        page_size=page_size,
        active_filters=active_filters,
    )

    return DecisionROIDashboardResponse(**dashboard_data)
