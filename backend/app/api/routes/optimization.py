"""
SupplyPrescript — Optimization API Router (Day 14)
==================================================
Production FastAPI router for prescriptive supply-chain optimization.
Evaluates shipment delay risk with active ML models, executes mathematical optimization,
validates hard business constraints (budget, capacity, inventory, delivery),
and returns the top feasible prescriptive decisions with comprehensive trade-off analytics.

Endpoint:
    POST /api/optimize
"""

from __future__ import annotations

import logging
import math
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.shipment import Shipment
from app.models.supplier import Supplier
from optimization.alternative_evaluator import evaluate_alternatives, validate_optimization_solution
from optimization.alternatives import generate_alternatives_for_shipment
from optimization.config import ScenarioConfig, get_baseline_scenario, load_scenario_config
from optimization.decision_ranker import rank_alternatives
from optimization.decision_schemas import (
    AlternativeEvaluationResponse,
    AlternativeGenerationRequest,
    AlternativeOption,
    BaselineSummary,
    ConstraintViolation,
    FeasibilityStatus,
    OptimizationConstraintCheck,
    OptimizationMetadata,
    OptimizationOption,
    OptimizationPredictionSummary,
    OptimizationRequest,
    OptimizationResponse,
    RecommendationStatus,
)

logger = logging.getLogger("app.api.routes.optimization")

router = APIRouter(tags=["Optimization"])

SUPPORTED_SCENARIOS: Set[str] = {
    "baseline",
    "baseline_supply_chain",
    "budget_constrained",
    "delay_sensitive",
    "risk_averse",
    "expedited_service",
    "inventory_buffering",
}

STRATEGY_MAP: Dict[str, Dict[str, str]] = {
    "A": {"strategy": "AIR_FREIGHT", "name": "Expedite using air freight"},
    "B": {"strategy": "SECONDARY_SUPPLIER", "name": "Switch to a qualified secondary supplier"},
    "C": {"strategy": "DELAY_LAUNCH", "name": "Delay the product launch"},
}


def _resolve_shipment_dict(shipment_id: str, db: Session) -> Dict[str, Any]:
    """
    Retrieve authoritative shipment and related product/supplier data from PostgreSQL.
    Prevents N+1 queries by executing targeted single-row lookups.
    """
    clean_id = shipment_id.strip()
    # Query shipment by string ID, uppercase, or zero-padded numeric string
    shipment = (
        db.query(Shipment)
        .filter(
            (Shipment.shipment_id == clean_id)
            | (Shipment.shipment_id == clean_id.upper())
            | (Shipment.shipment_id == f"SHIP{clean_id:0>3}" if clean_id.isdigit() else False)
            | (Shipment.shipment_id == f"SHP{clean_id:0>3}" if clean_id.isdigit() else False)
        )
        .first()
    )

    if not shipment:
        logger.warning("Shipment '%s' not found in database.", clean_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment with ID '{clean_id}' was not found in the database.",
        )

    # 1. Resolve product
    prod = db.query(Product).filter(Product.product_id == shipment.product_id).first()
    prod_name = prod.product_name if prod else shipment.product_id

    # 2. Resolve supplier
    supp = db.query(Supplier).filter(Supplier.supplier_id == shipment.supplier_id).first()
    supp_name = supp.supplier_name if supp else shipment.supplier_id
    origin = str(supp.origin if (supp and supp.origin) else shipment.origin or "Mumbai")
    dest = str(shipment.destination or "Delhi")

    # 3. Resolve inventory & demand
    inv_level = int(shipment.inventory_level) if shipment.inventory_level is not None else 100
    demand = int(shipment.demand) if shipment.demand is not None else 150

    supp_rel = (
        float(supp.supplier_reliability)
        if (supp and supp.supplier_reliability is not None)
        else float(shipment.supplier_reliability or 0.85)
    )

    return {
        "shipment_id": shipment.shipment_id,
        "product_id": shipment.product_id,
        "product_name": prod_name,
        "supplier_id": shipment.supplier_id,
        "supplier_name": supp_name,
        "origin": origin,
        "destination": dest,
        "quantity": float(shipment.quantity),
        "unit_cost": float(shipment.unit_cost),
        "shipping_cost": float(shipment.shipping_cost),
        "lead_time": float(shipment.lead_time),
        "delay_days": float(shipment.delay_days),
        "supplier_reliability": supp_rel,
        "historical_avg_delay": 1.0,
        "inventory_level": inv_level,
        "demand": demand,
        "transport_mode": shipment.transport_mode,
        "priority": shipment.priority,
        "season": "Post-Monsoon",
    }


def _run_alternative_pipeline(
    shipment_dict: Dict[str, Any],
    config: ScenarioConfig,
    db: Session,
    save_to_database: bool = False,
) -> AlternativeEvaluationResponse:
    """Core prescriptive optimization pipeline: generate -> evaluate -> rank -> persist."""
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

    ranked_alternatives, recommended_id, rec_status, reason, trade_offs = rank_alternatives(
        alternatives=audited_alternatives,
        baseline=baseline,
        config=config,
        validation_reports=reports,
    )

    if save_to_database and db is not None:
        try:
            from app.models.recommendation import Recommendation
            from app.models.decision import Decision
            from app.models.prediction import Prediction

            pred = (
                db.query(Prediction)
                .filter(Prediction.shipment_id == baseline.shipment_id)
                .order_by(Prediction.created_at.desc())
                .first()
            )

            if pred and recommended_id:
                winner = next((o for o in ranked_alternatives if o.option_id == recommended_id), None)
                if winner:
                    rec_type = (
                        "Expedite Shipment"
                        if winner.option_id == "A"
                        else ("Change Supplier" if winner.option_id == "B" else "Monitor Supplier")
                    )
                    rec_id = f"REC-OPT-{uuid.uuid4().hex[:8].upper()}"
                    new_rec = Recommendation(
                        recommendation_id=rec_id,
                        prediction_id=pred.id,
                        recommendation_type=rec_type,
                        recommendation_text=reason,
                        recommended_action=f"Adopt Option {winner.option_id}: {winner.name}",
                        priority=baseline.risk_level.title() if baseline.risk_level in ("LOW", "MEDIUM", "HIGH") else "Medium",
                        confidence_score=0.9200,
                        status="Active",
                    )
                    db.add(new_rec)
                    db.commit()
                    db.refresh(new_rec)

                    dec_id = f"DEC-OPT-{uuid.uuid4().hex[:8].upper()}"
                    new_dec = Decision(
                        decision_id=dec_id,
                        recommendation_id=new_rec.id,
                        decision=f"Approve Option {winner.option_id} ({winner.name})",
                        decision_reason=reason,
                        decision_source="Optimization",
                        status="Pending",
                    )
                    db.add(new_dec)
                    db.commit()
        except Exception as persist_exc:
            logger.warning("Could not persist recommendation to DB: %s", persist_exc)
            warnings.append(f"Persistence notice: {str(persist_exc)}")

    return AlternativeEvaluationResponse(
        shipment_id=baseline.shipment_id,
        scenario_id=config.scenario_name,
        baseline=baseline,
        alternatives=ranked_alternatives,
        recommended_option_id=recommended_id,
        recommendation_status=rec_status,
        recommendation_reason=reason,
        trade_off_analysis=trade_offs,
        model_version="v1.0",
        warnings=warnings,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )


# ===========================================================================
# POST /api/optimize — Production Prescriptive Optimization Endpoint (Day 14)
# ===========================================================================

@router.post(
    "/api/optimize",
    response_model=OptimizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Prescriptive Supply-Chain Optimization & Alternative Recommendation",
    description=(
        "Evaluates a target shipment's delay risk using active ML models, applies the Day 12 "
        "prescriptive optimization engine, audits hard business constraints (budget ceiling, "
        "supplier capacity, minimum inventory, delivery deadline), and returns the best "
        "ranked feasible alternatives with trade-off analysis."
    ),
    responses={
        200: {
            "description": "Optimization completed successfully; returns ranked feasible alternatives.",
            "content": {
                "application/json": {
                    "example": {
                        "shipment_id": "SHP1023",
                        "status": "SUCCESS",
                        "prediction": {
                            "delay_probability": 0.82,
                            "predicted_delay_days": 8.0,
                            "risk_level": "HIGH",
                            "model_version": "v1.0"
                        },
                        "options": [
                            {
                                "option_id": "A",
                                "strategy": "AIR_FREIGHT",
                                "name": "Expedite using air freight",
                                "status": "FEASIBLE",
                                "estimated_total_cost": 6500.0,
                                "additional_cost": 1250.0,
                                "estimated_delivery_days": 2.5,
                                "delay_probability": 0.12,
                                "risk_level": "LOW",
                                "objective_value": 6515.0,
                                "constraint_violations": [],
                                "assumptions": ["Air speedup 0.4x"],
                                "explanation": "Expediting via Air cuts transit to 2.5 days.",
                                "is_recommended": True
                            }
                        ],
                        "recommended_option_id": "A",
                        "recommendation_reason": "Option A recommended with optimal Day 12 objective cost $6,515.00.",
                        "constraint_checks": [
                            {
                                "name": "Maximum Budget",
                                "status": "SATISFIED",
                                "lhs_value": 6500.0,
                                "rhs_value": 50000.0,
                                "slack": 43500.0,
                                "description": "Applicable expenditure remains below ceiling."
                            }
                        ],
                        "warnings": [],
                        "optimization_metadata": {
                            "scenario_id": "baseline",
                            "solver_status": "OPTIMAL",
                            "runtime_ms": 14.5,
                            "model_version": "v1.0"
                        }
                    }
                }
            },
        },
        400: {"description": "Invalid input parameters or unsupported optimization scenario."},
        404: {"description": "Referenced shipment was not found in the database."},
        422: {"description": "Request validation error (e.g. num_options out of bounds)."},
        503: {"description": "ML inference model artifacts or optimization solver unavailable."},
        500: {"description": "Internal server error during optimization processing."},
    },
)
def optimize_shipment_endpoint(
    request: OptimizationRequest,
    db: Session = Depends(get_db),
) -> OptimizationResponse:
    """
    Execute Day 14 Production Prescriptive Optimization Flow:
    1. Validate Request & Scenario.
    2. Load Shipment & Operational Parameters from Database.
    3. Execute ML Inference for Delay Risk & Duration.
    4. Build Scenario & Generate 3 Decision Strategies (Air, Secondary Supplier, Delay Launch).
    5. Audit Against Hard Business Constraints (Budget, Capacity, Inventory, Delivery).
    6. Score & Rank via Day 12 Objective (min Z = C_total + C_delay + C_risk).
    7. Return Best Feasible Options with Telemetry & Explanations.
    """
    start_time = time.perf_counter()
    run_id = f"OPT-RUN-{uuid.uuid4().hex[:10].upper()}"

    # Step 1: Request Validation
    clean_shipment_id = request.shipment_id.strip() if request.shipment_id else ""
    if not clean_shipment_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'shipment_id' must not be blank.",
        )

    clean_scenario_id = (request.scenario_id or "baseline").strip().lower()
    if clean_scenario_id not in SUPPORTED_SCENARIOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported scenario_id '{request.scenario_id}'. "
                f"Supported scenarios are: {sorted(list(SUPPORTED_SCENARIOS))}"
            ),
        )

    # Step 2: Load Shipment & Related Data from PostgreSQL
    try:
        shipment_dict = _resolve_shipment_dict(clean_shipment_id, db)
    except HTTPException:
        raise
    except Exception as db_exc:
        logger.error("[%s] Database retrieval failure for shipment '%s': %s", run_id, clean_shipment_id, db_exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database query error while loading shipment parameters.",
        )

    # Step 3: Load Optimization Scenario Configuration
    try:
        config = load_scenario_config(overrides=request.scenario_overrides)
        config.scenario_name = clean_scenario_id
    except Exception as cfg_exc:
        logger.error("[%s] Scenario configuration loading error: %s", run_id, cfg_exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scenario configuration parameters: {str(cfg_exc)}",
        )

    # Step 4: Run Prescriptive Alternative Pipeline (Generate, Evaluate, Rank)
    try:
        eval_response = _run_alternative_pipeline(
            shipment_dict=shipment_dict,
            config=config,
            db=db,
            save_to_database=False,
        )
    except FileNotFoundError as fnf_err:
        logger.error("[%s] ML model artifacts unavailable: %s", run_id, fnf_err)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Predictive ML model artifacts are unavailable: {str(fnf_err)}",
        )
    except Exception as pipeline_exc:
        logger.error("[%s] Pipeline execution error: %s", run_id, pipeline_exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prescriptive optimization processing failure: {str(pipeline_exc)}",
        )

    baseline = eval_response.baseline

    # Step 5: Convert Alternatives to Day 14 OptimizationOption Schema
    converted_options: List[OptimizationOption] = []
    for opt in eval_response.alternatives:
        meta = STRATEGY_MAP.get(opt.option_id, {"strategy": "CUSTOM", "name": opt.name})
        risk_str = opt.risk_level.value if hasattr(opt.risk_level, "value") else str(opt.risk_level or "LOW")

        converted_options.append(
            OptimizationOption(
                option_id=opt.option_id,
                strategy=meta["strategy"],
                name=meta["name"],
                status=opt.feasibility.value,
                estimated_total_cost=opt.estimated_total_cost,
                additional_cost=opt.additional_cost,
                estimated_delivery_days=opt.estimated_delivery_days,
                delay_probability=opt.delay_probability,
                risk_level=risk_str,
                objective_value=opt.objective_value,
                constraint_violations=opt.constraint_violations,
                assumptions=opt.assumptions,
                explanation=opt.explanation,
                is_recommended=opt.is_recommended,
            )
        )

    # Slice to requested num_options
    final_options = converted_options[: request.num_options]

    # Step 6: Assemble Comprehensive Hard Constraint Audit Checks
    winner_opt = next((o for o in eval_response.alternatives if o.option_id == eval_response.recommended_option_id), None)
    eval_cost = winner_opt.estimated_total_cost if winner_opt else baseline.estimated_total_cost
    eval_delay = winner_opt.predicted_delay_days if winner_opt else baseline.predicted_delay_days

    b_limit = config.budget.max_total_cost
    b_lhs = float(eval_cost or 0.0)
    b_slack = round(b_limit - b_lhs, 2)
    b_status = "SATISFIED" if b_slack >= 0 else "VIOLATED"

    d_limit = config.delivery.maximum_acceptable_delay_days
    d_lhs = float(eval_delay or 0.0)
    d_slack = round(d_limit - d_lhs, 2)
    d_status = "SATISFIED" if d_slack >= 0 else "VIOLATED"

    cap_limit = float(config.supplier.default_max_capacity_units)
    cap_lhs = float(baseline.quantity)
    cap_slack = round(cap_limit - cap_lhs, 2)
    cap_status = "SATISFIED" if cap_slack >= 0 else "VIOLATED"

    constraint_checks = [
        OptimizationConstraintCheck(
            name="Maximum Budget",
            status=b_status,
            lhs_value=b_lhs,
            rhs_value=b_limit,
            slack=b_slack,
            description=f"Applicable expenditure ${b_lhs:,.2f} checked against ${b_limit:,.2f} ceiling.",
        ),
        OptimizationConstraintCheck(
            name="Delivery Delay Tolerance",
            status=d_status,
            lhs_value=d_lhs,
            rhs_value=d_limit,
            slack=d_slack,
            description=f"Predicted delay {d_lhs:.1f} days checked against {d_limit:.1f} days tolerance.",
        ),
        OptimizationConstraintCheck(
            name="Supplier Capacity",
            status=cap_status,
            lhs_value=cap_lhs,
            rhs_value=cap_limit,
            slack=cap_slack,
            description=f"Order quantity {cap_lhs:,.0f} units checked against {cap_limit:,.0f} units capacity.",
        ),
    ]

    if eval_response.recommendation_status == RecommendationStatus.FEASIBLE_RECOMMENDATION:
        top_status = "SUCCESS"
    elif eval_response.recommendation_status == RecommendationStatus.NO_FEASIBLE_OPTION:
        top_status = "NO_FEASIBLE_OPTION"
    else:
        top_status = eval_response.recommendation_status.value

    runtime_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    logger.info(
        "[%s] Optimization completed: shipment='%s', scenario='%s', status='%s', recommended='%s', runtime=%.2fms",
        run_id,
        clean_shipment_id,
        clean_scenario_id,
        top_status,
        eval_response.recommended_option_id,
        runtime_ms,
    )

    return OptimizationResponse(
        shipment_id=clean_shipment_id,
        status=top_status,
        prediction=OptimizationPredictionSummary(
            delay_probability=baseline.predicted_delay_probability,
            predicted_delay_days=baseline.predicted_delay_days,
            risk_level=baseline.risk_level,
            model_version=eval_response.model_version or "v1.0",
        ),
        options=final_options,
        recommended_option_id=eval_response.recommended_option_id,
        recommendation_reason=eval_response.recommendation_reason,
        constraint_checks=constraint_checks,
        warnings=eval_response.warnings,
        optimization_metadata=OptimizationMetadata(
            scenario_id=clean_scenario_id,
            solver_status="OPTIMAL" if top_status == "SUCCESS" else "INFEASIBLE",
            runtime_ms=runtime_ms,
            model_version=eval_response.model_version or "v1.0",
        ),
    )


# ===========================================================================
# Legacy / Scenario Endpoints (POST & GET /api/optimization/alternatives)
# ===========================================================================

@router.post(
    "/api/optimization/alternatives",
    response_model=AlternativeEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate 3 prescriptive decision alternatives for a shipment (Legacy Day 13)",
)
def generate_alternatives_endpoint(
    request: AlternativeGenerationRequest,
    db: Session = Depends(get_db),
) -> AlternativeEvaluationResponse:
    """POST /api/optimization/alternatives handler."""
    if not request.shipment_id or not request.shipment_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'shipment_id' must not be blank.",
        )

    shipment_dict = _resolve_shipment_dict(request.shipment_id.strip(), db)
    config = load_scenario_config(overrides=request.scenario_overrides)
    return _run_alternative_pipeline(shipment_dict, config, db, save_to_database=request.save_to_database)


@router.get(
    "/api/optimization/alternatives/{shipment_id}",
    response_model=AlternativeEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get prescriptive decision alternatives for a shipment by ID",
)
def get_alternatives_by_shipment_endpoint(
    shipment_id: str,
    max_budget: Optional[float] = Query(None, gt=0, description="Optional override for maximum total cost ($)"),
    max_delay: Optional[float] = Query(None, ge=0, description="Optional override for maximum acceptable delay (days)"),
    db: Session = Depends(get_db),
) -> AlternativeEvaluationResponse:
    """GET /api/optimization/alternatives/{shipment_id} handler."""
    if not shipment_id or not shipment_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shipment ID must not be empty.",
        )

    shipment_dict = _resolve_shipment_dict(shipment_id.strip(), db)

    overrides: Dict[str, Any] = {}
    if max_budget is not None:
        overrides.setdefault("budget", {})["max_total_cost"] = max_budget
    if max_delay is not None:
        overrides.setdefault("delivery", {})["maximum_acceptable_delay_days"] = max_delay

    config = load_scenario_config(overrides=overrides if overrides else None)
    return _run_alternative_pipeline(shipment_dict, config, db, save_to_database=False)
