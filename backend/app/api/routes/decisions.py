"""
SupplyPrescript — Decisions API Router (Day 17 & Day 18)
=========================================================
Secure decision execution & write-back governance workflow endpoints:
- POST /api/decisions: Authoritatively revalidates selected alternative, applies Day 15 hard
  constraint gates (budget, capacity, inventory, SLA), enforces idempotency, performs an actual
  atomic INSERT into the PostgreSQL database, and commits the transaction before returning success.
- GET /api/decisions: Retrieves paginated decision execution audit history with filtering.
- GET /api/decisions/{id}: Retrieves a single persisted decision record by unique decision_id.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, cast, String
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.decision import Decision
from app.models.outcome import Outcome
from app.models.prediction import Prediction
from app.models.recommendation import Recommendation
from app.models.shipment import Shipment
from app.models.supplier import Supplier
from app.api.routes.optimization import _resolve_shipment_dict
from app.schemas.outcome import (
    RecordOutcomeRequest,
    OutcomeComparisonResponse,
    OutcomeRecordResponse,
)
from app.services.outcome_comparison import compute_outcome_comparison
from optimization.alternative_evaluator import evaluate_alternatives
from optimization.alternatives import generate_alternatives_for_shipment
from optimization.config import ScenarioConfig, get_baseline_scenario, load_scenario_config
from optimization.decision_schemas import (
    DecisionHistoryItem,
    DecisionHistoryResponse,
    ExecuteDecisionRequest,
    ExecuteDecisionResponse,
    DecisionResponse,
    FeasibilityStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/decisions", tags=["Decisions"])


def _resolve_strategy(opt: Any) -> str:
    """Helper to authoritatively resolve strategy string from option."""
    strat = getattr(opt, "strategy", None)
    if strat:
        return str(strat)
    opt_id = getattr(opt, "option_id", "").upper()
    if opt_id == "A":
        return "AIR_FREIGHT"
    if opt_id == "B":
        return "SECONDARY_SUPPLIER"
    if opt_id == "C":
        return "DELAY_LAUNCH"
    return "AIR_FREIGHT"


@router.post(
    "",
    response_model=ExecuteDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create & Record an Authorized Decision in Database (Day 18 Write-Back)",
    description=(
        "Executes a secure write-back workflow. Validates target shipment, re-evaluates "
        "authoritative alternatives on the server, verifies Day 15 hard constraints (budget ceiling, "
        "supplier capacity, safety inventory, delivery window), enforces idempotency, executes an "
        "actual database INSERT into the operational PostgreSQL table, and commits the transaction. "
        "Does not execute automated real-world freight dispatch or financial disbursements."
    ),
    responses={
        201: {"description": "Decision successfully committed and recorded in database."},
        200: {"description": "Idempotent replay: previously recorded decision returned."},
        400: {"description": "Infeasible option, constraint violation, or strategy mismatch."},
        404: {"description": "Shipment or option not found."},
        409: {"description": "Idempotency conflict: key reused with conflicting payload."},
        500: {"description": "Database transaction failure."},
    },
)
def execute_decision_endpoint(
    request: ExecuteDecisionRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> ExecuteDecisionResponse:
    """POST /api/decisions handler."""
    # 1. Authoritative Shipment Resolution
    shipment_dict = _resolve_shipment_dict(request.shipment_id, db)
    clean_shipment_id = shipment_dict["shipment_id"]

    # 2. Server-Side Alternative Re-evaluation (Never trust client-supplied costs or flags!)
    config = get_baseline_scenario()
    baseline, raw_alternatives, warnings = generate_alternatives_for_shipment(
        shipment=shipment_dict,
        config=config,
        db=db,
    )

    audited_alternatives, reports = evaluate_alternatives(
        baseline=baseline,
        alternatives=raw_alternatives,
        config=config,
    )

    # 3. Match Target Option
    target_option_id = request.option_id.strip().upper()
    matched_option = next(
        (opt for opt in audited_alternatives if opt.option_id.upper() == target_option_id),
        None,
    )

    if not matched_option:
        valid_ids = [opt.option_id for opt in audited_alternatives]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Option '{request.option_id}' does not exist for shipment {clean_shipment_id}. "
                f"Available alternatives: {', '.join(valid_ids)}."
            ),
        )

    # 4. Strategy & Recommendation Consistency Verification
    resolved_strategy = _resolve_strategy(matched_option)
    requested_strat = request.recommendation or request.strategy
    if requested_strat:
        req_strat_norm = requested_strat.strip().upper().replace(" ", "_")
        opt_strat_norm = resolved_strategy.strip().upper().replace(" ", "_")
        if req_strat_norm != opt_strat_norm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Strategy mismatch: requested '{requested_strat}', but Option {matched_option.option_id} "
                    f"is configured as '{resolved_strategy}'."
                ),
            )

    # 5. Day 15 Safety Gate & Feasibility Enforcement
    is_feasible = matched_option.feasibility == FeasibilityStatus.FEASIBLE
    if not is_feasible:
        violations_summary = [
            f"{v.constraint_name} (actual: {v.actual_value}, limit: {v.limit_value})"
            for v in matched_option.constraint_violations
        ]
        detail_msg = (
            f"Cannot execute Option {matched_option.option_id} ({matched_option.name}): "
            f"it is classified as {matched_option.feasibility.value} and violates hard business constraints: "
            f"{', '.join(violations_summary) if violations_summary else 'unmet operational prerequisites'}."
        )
        logger.warning("Rejected execution of infeasible option: %s", detail_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail_msg,
        )

    # 6. Hard Budget Constraint Validation
    hard_budget_ceiling = 50000.0  # Baseline budget ceiling threshold ($50,000)
    if matched_option.estimated_total_cost is not None and matched_option.estimated_total_cost > hard_budget_ceiling:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Option {matched_option.option_id} violates the hard budget constraint: "
                f"estimated total cost (${matched_option.estimated_total_cost:,.2f}) exceeds "
                f"the maximum allowable budget ceiling (${hard_budget_ceiling:,.2f})."
            ),
        )

    # 7. Idempotency Check
    idemp_key = request.idempotency_key.strip() if request.idempotency_key else None
    if idemp_key:
        existing = db.query(Decision).filter(Decision.idempotency_key == idemp_key).first()
        if existing:
            # Check for matching payload
            existing_shipment_match = (existing.shipment_id == clean_shipment_id)
            existing_option_match = (
                existing.option_id and existing.option_id.upper() == matched_option.option_id.upper()
            )
            if existing_shipment_match and existing_option_match:
                logger.info(
                    "Idempotent decision replay for key '%s' (decision_id: %s)",
                    idemp_key,
                    existing.decision_id,
                )
                response.status_code = status.HTTP_200_OK

                cost_val = float(existing.predicted_cost or existing.estimated_total_cost or 0.0)
                delay_val = float(existing.predicted_delay if existing.predicted_delay is not None else (existing.delay_probability or 0.0))
                time_iso = (
                    existing.decision_time.isoformat()
                    if existing.decision_time
                    else (existing.created_at.isoformat() if existing.created_at else datetime.now(timezone.utc).isoformat())
                )

                return ExecuteDecisionResponse(
                    decision_id=existing.decision_id,
                    shipment_id=existing.shipment_id,
                    user_id=existing.user_id or existing.approved_by or "usr_ops_manager",
                    recommendation=existing.strategy or resolved_strategy,
                    predicted_cost=f"{cost_val:.2f}",
                    predicted_delay=delay_val,
                    decision_time=time_iso,
                    status=existing.status,
                    option_id=existing.option_id or matched_option.option_id,
                    strategy=existing.strategy or matched_option.strategy or "AIR_FREIGHT",
                    estimated_total_cost=cost_val,
                    currency=existing.currency or "USD",
                    estimated_delivery_days=float(existing.estimated_delivery_days or matched_option.estimated_delivery_days or 0.0),
                    delay_probability=float(existing.delay_probability) if existing.delay_probability is not None else matched_option.delay_probability,
                    constraint_validation=existing.constraint_validation_snapshot or {
                        "budget": "PASS",
                        "inventory": "PASS",
                        "supplier_capacity": "PASS",
                        "delivery": "PASS",
                    },
                    external_action_status=existing.external_action_status or "NOT_EXECUTED",
                    message="Decision previously recorded (idempotent request). No external booking was made.",
                    recorded_at=time_iso,
                    idempotency_key=existing.idempotency_key,
                )
            else:
                logger.warning(
                    "Conflicting idempotency key '%s' reused for different decision (existing: %s/%s, requested: %s/%s)",
                    idemp_key,
                    existing.shipment_id,
                    existing.option_id,
                    clean_shipment_id,
                    matched_option.option_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Idempotency conflict: key '{idemp_key}' was previously used to record a "
                        f"different decision for shipment {existing.shipment_id} (Option {existing.option_id}). "
                        f"Reusing an idempotency key with conflicting parameters is prohibited."
                    ),
                )
    else:
        idemp_key = f"IDEMP-{uuid.uuid4().hex[:12].upper()}"

    # 8. Resolve/Create Recommendation Foreign Key
    pred = (
        db.query(Prediction)
        .filter(Prediction.shipment_id == clean_shipment_id)
        .order_by(Prediction.created_at.desc())
        .first()
    )

    rec_record = None
    if pred:
        rec_record = (
            db.query(Recommendation)
            .filter(Recommendation.prediction_id == pred.id)
            .first()
        )

    rec_id_str = f"REC-EXEC-{uuid.uuid4().hex[:8].upper()}"
    if not rec_record and pred:
        rec_type = (
            "Expedite Shipment"
            if matched_option.option_id == "A"
            else ("Change Supplier" if matched_option.option_id == "B" else "Monitor Supplier")
        )
        rec_record = Recommendation(
            recommendation_id=rec_id_str,
            prediction_id=pred.id,
            recommendation_type=rec_type,
            recommendation_text=matched_option.explanation or f"Adopt Option {matched_option.option_id}: {matched_option.name}",
            recommended_action=f"Adopt Option {matched_option.option_id}: {matched_option.name}",
            priority="High",
            confidence_score=Decimal("0.9200"),
            status="Active",
        )
        db.add(rec_record)
        db.flush()

    # 9. Compute Authoritative Values
    dec_id = f"DEC-EXEC-{uuid.uuid4().hex[:8].upper()}"
    now_utc = datetime.now(timezone.utc)
    
    authoritative_cost = float(matched_option.estimated_total_cost or 0.0)
    cost_str = f"{authoritative_cost:.2f}"
    cost_dec = Decimal(cost_str)
    
    # predicted_delay: defined as the estimated delay in days (not total transit time)
    authoritative_predicted_delay = float(matched_option.predicted_delay_days if matched_option.predicted_delay_days is not None else 0.0)
    delay_dec = Decimal(f"{authoritative_predicted_delay:.2f}")

    delivery_dec = Decimal(str(round(matched_option.estimated_delivery_days, 2))) if matched_option.estimated_delivery_days is not None else None
    prob_dec = Decimal(str(round(matched_option.delay_probability, 4))) if matched_option.delay_probability is not None else None

    # Derive user_id (In dev unauthenticated mode, derived from principal/header or fallback)
    resolved_user_id = request.user_id or request.approved_by or "usr_ops_manager"

    constraint_snapshot = {
        "budget": "PASS",
        "inventory": "PASS",
        "supplier_capacity": "PASS",
        "delivery": "PASS",
    }

    # 10. Actual Database INSERT & Commit (Day 18 Write-Back Engine)
    new_dec = Decision(
        decision_id=dec_id,
        recommendation_id=rec_record.id if rec_record else 1,
        decision=f"Execute Decision: Option {matched_option.option_id} ({matched_option.name})",
        decision_reason=request.notes or matched_option.explanation or f"Approved Option {matched_option.option_id}",
        decision_source="Optimization",
        approved_by=request.approved_by or "Operations Manager",
        status="RECORDED",
        shipment_id=clean_shipment_id,
        optimization_run_id=request.optimization_run_id or f"OPT-RUN-{uuid.uuid4().hex[:8].upper()}",
        option_id=matched_option.option_id,
        strategy=resolved_strategy,
        estimated_total_cost=cost_dec,
        currency="USD",
        estimated_delivery_days=delivery_dec,
        delay_probability=prob_dec,
        constraint_validation_snapshot=constraint_snapshot,
        idempotency_key=idemp_key,
        external_action_status="NOT_EXECUTED",
        user_id=resolved_user_id,
        predicted_cost=cost_dec,
        predicted_delay=delay_dec,
        decision_time=now_utc,
    )

    try:
        db.add(new_dec)
        db.commit()
        db.refresh(new_dec)
        response.status_code = status.HTTP_201_CREATED
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to persist execution decision: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database transaction failed while recording execution decision.",
        )

    return ExecuteDecisionResponse(
        decision_id=new_dec.decision_id,
        shipment_id=clean_shipment_id,
        user_id=resolved_user_id,
        recommendation=resolved_strategy,
        predicted_cost=cost_str,
        predicted_delay=authoritative_predicted_delay,
        decision_time=now_utc.isoformat(),
        status="RECORDED",
        option_id=matched_option.option_id,
        strategy=resolved_strategy,
        estimated_total_cost=authoritative_cost,
        currency="USD",
        estimated_delivery_days=float(matched_option.estimated_delivery_days or 0.0),
        delay_probability=matched_option.delay_probability,
        constraint_validation=constraint_snapshot,
        external_action_status="NOT_EXECUTED",
        message="Decision recorded successfully. No external booking was made.",
        recorded_at=now_utc.isoformat(),
        idempotency_key=idemp_key,
    )


@router.get(
    "",
    response_model=DecisionHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="List Decision Records (Day 18 Write-Back Architecture)",
    description="Returns paginated decision audit records from PostgreSQL with filtering by shipment, user, status, and date range.",
)
def get_decisions_endpoint(
    shipment_id: Optional[str] = Query(None, description="Filter decisions by shipment identifier"),
    user_id: Optional[str] = Query(None, description="Filter decisions by operating user ID"),
    status: Optional[str] = Query(None, description="Filter decisions by status (e.g. RECORDED, Pending)"),
    start_time: Optional[datetime] = Query(None, description="Filter decisions created on or after this timestamp"),
    end_time: Optional[datetime] = Query(None, description="Filter decisions created on or before this timestamp"),
    limit: int = Query(20, ge=1, le=200, description="Maximum decision records to return"),
    offset: int = Query(0, ge=0, description="Items skipped for pagination"),
    db: Session = Depends(get_db),
) -> DecisionHistoryResponse:
    """GET /api/decisions handler."""
    query = db.query(Decision)

    if shipment_id:
        clean_id = shipment_id.strip()
        match = re.search(r"^(?:SHIP|SHP)?(\d+)$", clean_id, re.IGNORECASE)
        candidate_ids = {clean_id}
        if match:
            try:
                num = int(match.group(1))
                candidate_ids.add(f"SHIP{num:06d}")
                candidate_ids.add(f"SHIP{num:03d}")
                candidate_ids.add(f"SHP{num:04d}")
            except ValueError:
                pass
        query = query.filter(Decision.shipment_id.in_(list(candidate_ids)))

    if user_id:
        query = query.filter(Decision.user_id == user_id.strip())

    if status:
        query = query.filter(Decision.status.ilike(status.strip()))

    if start_time:
        query = query.filter(Decision.decision_time >= start_time)

    if end_time:
        query = query.filter(Decision.decision_time <= end_time)

    total = query.count()

    records = (
        query.order_by(Decision.decision_time.desc(), Decision.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items: List[DecisionHistoryItem] = []
    for d in records:
        cost_val = float(d.predicted_cost or d.estimated_total_cost or 0.0)
        delay_val = float(d.predicted_delay if d.predicted_delay is not None else (d.delay_probability or 0.0))
        time_iso = (
            d.decision_time.isoformat()
            if d.decision_time
            else (d.created_at.isoformat() if d.created_at else datetime.now(timezone.utc).isoformat())
        )

        items.append(
            DecisionHistoryItem(
                decision_id=d.decision_id,
                shipment_id=d.shipment_id or "UNKNOWN",
                user_id=d.user_id or d.approved_by or "usr_ops_manager",
                recommendation=d.strategy or d.decision,
                predicted_cost=f"{cost_val:.2f}",
                predicted_delay=delay_val,
                decision_time=time_iso,
                status=d.status,
                option_id=d.option_id,
                strategy=d.strategy or d.recommendation,
                decision=d.decision,
                decision_reason=d.decision_reason,
                estimated_total_cost=cost_val,
                currency=d.currency or "USD",
                estimated_delivery_days=float(d.estimated_delivery_days) if d.estimated_delivery_days is not None else None,
                external_action_status=d.external_action_status or "NOT_EXECUTED",
                approved_by=d.approved_by or d.user_id,
                created_at=time_iso,
            )
        )

    return DecisionHistoryResponse(
        items=items,
        decisions=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{decision_id}",
    response_model=ExecuteDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Decision Record by ID (Day 18 Write-Back Architecture)",
    description="Queries the operational database for a single decision record by decision_id.",
    responses={
        200: {"description": "Persisted decision record returned."},
        404: {"description": "Decision record not found."},
    },
)
def get_decision_by_id_endpoint(
    decision_id: str,
    db: Session = Depends(get_db),
) -> ExecuteDecisionResponse:
    """GET /api/decisions/{id} handler."""
    clean_id = decision_id.strip()
    if not clean_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid decision identifier is required.",
        )

    record = (
        db.query(Decision)
        .filter(or_(Decision.decision_id == clean_id, cast(Decision.id, String) == clean_id))
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision record '{clean_id}' was not found in operational database.",
        )

    cost_val = float(record.predicted_cost or record.estimated_total_cost or 0.0)
    delay_val = float(record.predicted_delay if record.predicted_delay is not None else (record.delay_probability or 0.0))
    time_iso = (
        record.decision_time.isoformat()
        if record.decision_time
        else (record.created_at.isoformat() if record.created_at else datetime.now(timezone.utc).isoformat())
    )

    return ExecuteDecisionResponse(
        decision_id=record.decision_id,
        shipment_id=record.shipment_id or "UNKNOWN",
        user_id=record.user_id or record.approved_by or "usr_ops_manager",
        recommendation=record.strategy or record.decision,
        predicted_cost=f"{cost_val:.2f}",
        predicted_delay=delay_val,
        decision_time=time_iso,
        status=record.status,
        option_id=record.option_id,
        strategy=record.strategy or "AIR_FREIGHT",
        estimated_total_cost=cost_val,
        currency=record.currency or "USD",
        estimated_delivery_days=float(record.estimated_delivery_days) if record.estimated_delivery_days is not None else 0.0,
        delay_probability=float(record.delay_probability) if record.delay_probability is not None else None,
        constraint_validation=record.constraint_validation_snapshot or {
            "budget": "PASS",
            "inventory": "PASS",
            "supplier_capacity": "PASS",
            "delivery": "PASS",
        },
        external_action_status=record.external_action_status or "NOT_EXECUTED",
        message="Persisted decision record retrieved from database.",
        recorded_at=time_iso,
        idempotency_key=record.idempotency_key,
    )


@router.post(
    "/{decision_id}/outcome",
    response_model=OutcomeComparisonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Actual Operational Outcome for a Decision (Day 19 Closed-Loop)",
    description=(
        "Records the verified real-world operational outcome (actual cost, delivery date, delay, supplier, quantity) "
        "for a previously authorized and committed decision. Compares predicted outcomes against actual outcomes "
        "and commits the immutable outcome to the operational PostgreSQL database. Enforces one final outcome per decision."
    ),
    responses={
        201: {"description": "Operational outcome recorded and comparison generated successfully."},
        400: {"description": "Invalid input, dates, or negative cost/quantity."},
        404: {"description": "Decision record not found."},
        409: {"description": "An outcome has already been recorded for this decision."},
        500: {"description": "Database persistence failure."},
    },
)
def record_decision_outcome_endpoint(
    decision_id: str,
    request: RecordOutcomeRequest,
    db: Session = Depends(get_db),
) -> OutcomeComparisonResponse:
    """POST /api/decisions/{decision_id}/outcome handler."""
    clean_id = decision_id.strip()
    if not clean_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid decision identifier is required in URL path.",
        )

    # 1. Retrieve the Decision from PostgreSQL
    decision = (
        db.query(Decision)
        .filter(or_(Decision.decision_id == clean_id, cast(Decision.id, String) == clean_id))
        .first()
    )
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision record '{clean_id}' was not found in operational database.",
        )

    # 2. Enforce one final outcome per decision
    existing_outcome = (
        db.query(Outcome)
        .filter(Outcome.decision_id == decision.id)
        .first()
    )
    if existing_outcome:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"An operational outcome has already been recorded for decision '{decision.decision_id}' "
                f"(Outcome ID: '{existing_outcome.outcome_id}'). Duplicate outcomes are rejected."
            ),
        )

    # 3. Retrieve Target Shipment & Baseline Delivery Date
    shipment = None
    if decision.shipment_id:
        shipment = (
            db.query(Shipment)
            .filter(Shipment.shipment_id == decision.shipment_id)
            .first()
        )

    baseline_date = request.baseline_delivery_date
    if not baseline_date and shipment:
        baseline_date = shipment.expected_delivery_date

    # 4. Calculate Authoritative Actual Delay
    actual_delay: Optional[Decimal] = None
    if request.actual_delay is not None:
        actual_delay = request.actual_delay
    elif request.actual_delivery_date is not None:
        if baseline_date:
            days_diff = (request.actual_delivery_date - baseline_date).days
            actual_delay = Decimal(str(max(0, days_diff)))
        else:
            logger.warning(f"Baseline delivery date missing for decision '{decision.decision_id}'. Actual delay left unset.")
    else:
        # Undelivered shipment: do not fabricate delay
        actual_delay = None

    # 5. Resolve Supplier & Quantity
    act_supplier = request.actual_supplier.strip() if request.actual_supplier else None
    if not act_supplier and shipment:
        act_supplier = shipment.supplier_id

    act_quantity = request.actual_quantity
    if act_quantity is None and shipment and shipment.quantity:
        act_quantity = Decimal(str(shipment.quantity))

    # 6. Generate Outcome ID & Persist Record
    outcome_id = f"OUT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    outcome_status = request.outcome_status or ("DELIVERED" if request.actual_delivery_date else "RECORDED")
    now_utc = datetime.now(timezone.utc)

    outcome_record = Outcome(
        outcome_id=outcome_id,
        decision_id=decision.id,
        decision_business_id=decision.decision_id,
        shipment_id=decision.shipment_id,
        actual_cost=request.actual_cost,
        currency=request.currency or decision.currency or "USD",
        actual_delivery_date=request.actual_delivery_date,
        actual_delay=actual_delay,
        actual_delay_days=int(round(float(actual_delay))) if actual_delay is not None else 0,
        baseline_delivery_date=baseline_date,
        actual_supplier=act_supplier,
        actual_quantity=act_quantity,
        outcome_status=outcome_status,
        source=request.source or "manual_entry",
        notes=request.notes,
        outcome_notes=request.notes,
        recorded_by=request.recorded_by or getattr(decision, "user_id", None) or "usr_ops_manager",
        recorded_at=now_utc,
        updated_at=now_utc,
    )

    try:
        db.add(outcome_record)
        db.commit()
        db.refresh(outcome_record)
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to persist outcome record for decision '{decision.decision_id}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction failure recording outcome: {str(exc)}",
        )

    # 7. Compute Closed-Loop Comparison
    comparison = compute_outcome_comparison(
        decision=decision,
        outcome=outcome_record,
        shipment=shipment,
    )

    outcome_schema = OutcomeRecordResponse(
        outcome_id=outcome_record.outcome_id,
        decision_id=decision.decision_id,
        shipment_id=outcome_record.shipment_id,
        actual_cost=outcome_record.actual_cost,
        currency=outcome_record.currency or "USD",
        actual_delivery_date=outcome_record.actual_delivery_date,
        actual_delay=outcome_record.actual_delay,
        baseline_delivery_date=outcome_record.baseline_delivery_date,
        actual_supplier=outcome_record.actual_supplier,
        actual_quantity=outcome_record.actual_quantity,
        outcome_status=outcome_record.outcome_status,
        source=outcome_record.source or "manual_entry",
        notes=outcome_record.notes,
        recorded_by=outcome_record.recorded_by,
        recorded_at=outcome_record.recorded_at,
        updated_at=outcome_record.updated_at,
    )
    comparison["outcome"] = outcome_schema

    return OutcomeComparisonResponse(**comparison)


@router.get(
    "/{decision_id}/outcome",
    response_model=OutcomeComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Actual Operational Outcome & Comparison for a Decision (Day 19)",
    description=(
        "Retrieves the recorded actual operational outcome and closed-loop predicted vs actual "
        "variance comparison for a specific decision. Returns 404 if no outcome has been recorded."
    ),
    responses={
        200: {"description": "Recorded outcome and comparison retrieved successfully."},
        404: {"description": "Decision or outcome not found."},
    },
)
def get_decision_outcome_endpoint(
    decision_id: str,
    db: Session = Depends(get_db),
) -> OutcomeComparisonResponse:
    """GET /api/decisions/{decision_id}/outcome handler."""
    clean_id = decision_id.strip()
    if not clean_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid decision identifier is required.",
        )

    # 1. Retrieve the Decision
    decision = (
        db.query(Decision)
        .filter(or_(Decision.decision_id == clean_id, cast(Decision.id, String) == clean_id))
        .first()
    )
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision record '{clean_id}' was not found in operational database.",
        )

    # 2. Retrieve Associated Outcome
    outcome = (
        db.query(Outcome)
        .filter(Outcome.decision_id == decision.id)
        .first()
    )
    if not outcome:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No operational outcome has been recorded yet for decision '{decision.decision_id}'.",
        )

    # 3. Retrieve Target Shipment
    shipment = None
    if decision.shipment_id:
        shipment = (
            db.query(Shipment)
            .filter(Shipment.shipment_id == decision.shipment_id)
            .first()
        )

    # 4. Compute Comparison
    comparison = compute_outcome_comparison(
        decision=decision,
        outcome=outcome,
        shipment=shipment,
    )

    outcome_schema = OutcomeRecordResponse(
        outcome_id=outcome.outcome_id,
        decision_id=decision.decision_id,
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
    comparison["outcome"] = outcome_schema

    return OutcomeComparisonResponse(**comparison)

