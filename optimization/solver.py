"""
SupplyPrescript — Optimization Engine Solver Module
===================================================
Production mathematical optimization solver powered by PuLP (MILP).
Formulates and solves prescriptive supply-chain allocation problems,
minimizing total procurement, transportation, inventory carrying,
delay penalty, and operational disruption risk costs subject to
budget, capacity, inventory, and delivery constraints.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import pulp

from optimization.config import ScenarioConfig, get_baseline_scenario, load_scenario_config
from optimization.constraints import (
    AppliedConstraint,
    ConstraintRegistry,
    apply_business_constraints,
)
from optimization.objective import ObjectiveExpressions, build_objective
from optimization.results import (
    ConstraintCheckResult,
    ConstraintSummary,
    DecisionAllocation,
    InfeasibilityReport,
    InventoryResult,
    ObjectiveSummary,
    OptimizationResult,
    SupplierCapacityUtilization,
)
from optimization.validation import (
    InfeasibilityDiagnostic,
    PreSolveValidationReport,
    diagnose_infeasibility,
    validate_optimization_inputs,
)
from optimization.variables import (
    CandidateOption,
    OptimizationVariables,
    ProductData,
    create_decision_variables,
)

logger = logging.getLogger("optimization.solver")

# In-memory ML inference cache within optimization session: feature_key -> prediction_dict
_PREDICTION_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}


def clear_prediction_cache() -> None:
    """Clear internal in-memory prediction cache."""
    global _PREDICTION_CACHE
    _PREDICTION_CACHE.clear()


def build_optimization_problem(
    candidate_options: List[CandidateOption],
    products: List[ProductData],
    config: ScenarioConfig,
) -> Tuple[pulp.LpProblem, OptimizationVariables, ObjectiveExpressions, ConstraintRegistry]:
    """
    Build and assemble a complete PuLP optimization problem instance.
    Sets up decision variables, multi-component objective, and operational constraints.
    """
    problem = pulp.LpProblem(
        name=f"SupplyPrescript_{config.scenario_name}",
        sense=pulp.LpMinimize,
    )

    # 1. Decision Variables (x[s, p], q[s, p, m], I[p], u[p])
    variables = create_decision_variables(
        problem=problem,
        candidate_options=candidate_options,
        products=products,
        config=config,
    )

    # 2. Objective Function (Procurement + Shipping + Inventory + Delay + Risk + Shortage)
    objectives = build_objective(
        problem=problem,
        variables=variables,
        candidate_options=candidate_options,
        products=products,
        config=config,
    )

    # 3. Business Constraints (Budget, Inventory, Capacity, Delay, Consistency)
    constraint_registry = apply_business_constraints(
        problem=problem,
        variables=variables,
        objectives=objectives,
        candidate_options=candidate_options,
        products=products,
        config=config,
    )

    return problem, variables, objectives, constraint_registry


def _resolve_pulp_solver(config: ScenarioConfig) -> Any:
    """
    Pick and configure an available MILP solver with configured timeout and message suppression.
    Prefers HiGHS, falls back to CBC, GLPK, or default solver.
    """
    time_limit = config.optimization.time_limit_seconds
    msg = config.optimization.msg

    # 1. HiGHS (highspy)
    if hasattr(pulp, "HiGHS") and "HiGHS" in pulp.listSolvers(onlyAvailable=True):
        try:
            return pulp.HiGHS(msg=msg, timeLimit=time_limit)
        except Exception as e:
            logger.debug("HiGHS solver instantiation failed: %s", e)

    # 2. CBC CMD
    if hasattr(pulp, "PULP_CBC_CMD") and "PULP_CBC_CMD" in pulp.listSolvers(onlyAvailable=True):
        try:
            return pulp.PULP_CBC_CMD(msg=msg, timeLimit=time_limit)
        except Exception as e:
            logger.debug("CBC solver instantiation failed: %s", e)

    # 3. First available solver fallback
    available = pulp.listSolvers(onlyAvailable=True)
    if available:
        solver_name = available[0]
        solver_cls = getattr(pulp, solver_name, None)
        if solver_cls:
            try:
                return solver_cls(msg=msg)
            except Exception as e:
                logger.debug("Fallback solver %s instantiation failed: %s", solver_name, e)

    # 4. PuLP default
    return None


def enrich_candidate_options_with_ml(
    candidate_options: List[CandidateOption],
    config: ScenarioConfig,
    cache_predictions: bool = True,
) -> Tuple[List[CandidateOption], Optional[str], Optional[str], List[str]]:
    """
    Safely score candidate options using the registered ML prediction service (v1.0 XGBoost).
    Caches predictions within the run to avoid redundant calls for identical feature tuples.
    Returns (enriched_options, active_model_version, prediction_timestamp, warnings).
    """
    warnings: List[str] = []
    active_version: Optional[str] = None
    prediction_timestamp: Optional[str] = None

    try:
        from ml.predict import predict_shipment
    except ImportError as imp_err:
        warnings.append(f"ML prediction module unavailable ({imp_err}). Using baseline route estimates.")
        return candidate_options, None, None, warnings

    for opt in candidate_options:
        # Construct feature key for caching
        feature_key = (
            opt.supplier_id,
            getattr(opt, "supplier_reliability", 0.85),
            opt.lead_time_days,
            opt.transport_mode,
            opt.distance_km,
        )

        if cache_predictions and feature_key in _PREDICTION_CACHE:
            pred = _PREDICTION_CACHE[feature_key]
        else:
            feature_dict = {
                "supplier_reliability": getattr(opt, "supplier_reliability", 0.85),
                "historical_avg_delay": 1.0,
                "lead_time": opt.lead_time_days,
                "inventory_level": 100,
                "demand": 150,
                "quantity": 100,
                "shipping_cost": opt.shipping_cost_per_unit * 100,
                "distance": opt.distance_km,
                "transport_mode": opt.transport_mode,
                "season": "Post-Monsoon",
                "priority": "Medium",
            }

            try:
                pred = predict_shipment(feature_dict)
                if cache_predictions:
                    _PREDICTION_CACHE[feature_key] = pred
            except Exception as ml_exc:
                logger.debug("ML inference error for option %s: %s", feature_key, ml_exc)
                pred = {
                    "delay_probability": opt.predicted_delay_probability,
                    "predicted_delay_days": opt.predicted_delay_days,
                    "model_version": "fallback",
                    "prediction_timestamp": datetime.now(timezone.utc).isoformat(),
                }
                warnings.append(f"Prediction fallback for {opt.supplier_id}-{opt.transport_mode}: {ml_exc}")

        # Update candidate option values
        prob = float(pred.get("delay_probability", opt.predicted_delay_probability))
        days = float(pred.get("predicted_delay_days", opt.predicted_delay_days))
        opt.predicted_delay_probability = round(prob, 4)
        opt.predicted_delay_days = round(days, 2)

        # Expected delay penalty cost per unit: P(delay) * (daily_delay_penalty * predicted_delay_days / 100)
        daily_penalty = config.delivery.daily_delay_penalty
        opt.expected_delay_cost_per_unit = round(prob * (daily_penalty * days / 100.0), 4)

        # Operational risk cost per unit based on supplier unreliability: (1 - reliability) * operational_risk_cost_rate
        risk_rate = config.risk.operational_risk_cost_rate if hasattr(config, "risk") else 0.0
        if risk_rate > 0:
            rel = getattr(opt, "supplier_reliability", 1.0)
            opt.expected_risk_cost_per_unit = round(max(0.0, 1.0 - rel) * risk_rate, 4)

        if active_version is None and pred.get("model_version"):
            active_version = str(pred["model_version"])
        if prediction_timestamp is None and pred.get("prediction_timestamp"):
            prediction_timestamp = str(pred["prediction_timestamp"])

    return candidate_options, active_version, prediction_timestamp, warnings


def solve_supply_chain(
    suppliers: Optional[Any] = None,
    products: Optional[Any] = None,
    demand: Optional[Any] = None,
    inventory: Optional[Any] = None,
    shipping_options: Optional[Any] = None,
    scenario: Optional[Union[str, ScenarioConfig, Dict[str, Any]]] = None,
    *,
    candidate_options: Optional[List[CandidateOption]] = None,
    product_data: Optional[List[ProductData]] = None,
    use_ml_predictions: bool = False,
) -> OptimizationResult:
    """
    Return the best feasible supply-chain plan.

    Supports both high-level raw parameters (suppliers, products, demand, inventory, shipping_options)
    and pre-constructed candidate options and product data structures.

    Solver statuses supported:
    - OPTIMAL
    - FEASIBLE
    - INFEASIBLE
    - UNBOUNDED
    - TIME_LIMIT
    - ERROR
    """
    start_time = time.perf_counter()

    # 1. Resolve Scenario Configuration
    if scenario is None:
        cfg = get_baseline_scenario()
    elif isinstance(scenario, ScenarioConfig):
        cfg = scenario
    elif isinstance(scenario, str):
        from optimization.scenarios import create_scenario
        cfg = create_scenario(scenario)
    elif isinstance(scenario, dict):
        cfg = load_scenario_config(overrides=scenario)
    else:
        cfg = get_baseline_scenario()

    constraint_summary = ConstraintSummary(
        budget_limit=cfg.budget.max_total_cost,
        minimum_inventory_units=cfg.inventory.minimum_required_units,
        maximum_acceptable_delay_days=cfg.delivery.maximum_acceptable_delay_days,
        default_supplier_capacity_units=cfg.supplier.default_max_capacity_units,
    )

    # 2. Resolve Products and Candidate Options
    resolved_candidates: List[CandidateOption] = []
    resolved_products: List[ProductData] = []
    conversion_warnings: List[str] = []

    if candidate_options is not None and product_data is not None:
        resolved_candidates = list(candidate_options)
        resolved_products = list(product_data)
    else:
        # Convert raw inputs if provided
        try:
            resolved_candidates, resolved_products, conv_warn = _convert_raw_inputs(
                suppliers=suppliers,
                products=products,
                demand=demand,
                inventory=inventory,
                shipping_options=shipping_options,
                config=cfg,
            )
            conversion_warnings.extend(conv_warn)
        except Exception as conv_err:
            elapsed = time.perf_counter() - start_time
            logger.error("Failed to parse supply-chain input data: %s", conv_err)
            return OptimizationResult(
                status="ERROR",
                scenario_id=cfg.scenario_name,
                scenario_name=cfg.scenario_name,
                objective_value=None,
                currency=cfg.budget.currency,
                cost_breakdown={
                    "procurement_cost": None,
                    "shipping_cost": None,
                    "inventory_cost": None,
                    "delay_penalty": None,
                    "risk_cost": None,
                    "shortage_cost": None,
                },
                decisions=[],
                constraint_checks=[],
                warnings=[f"Input parsing error: {conv_err}"],
                model_metadata={"solver": None, "model_version": None, "solve_time_seconds": round(elapsed, 4)},
                solver_name="None",
                solve_time_seconds=round(elapsed, 4),
                objective=ObjectiveSummary(name=cfg.optimization.objective, total_cost=None, currency=cfg.budget.currency),
                constraints=constraint_summary,
            )

    # 3. Optional ML Enrichment
    active_model_version: Optional[str] = None
    pred_timestamp: Optional[str] = None
    ml_warnings: List[str] = []
    if use_ml_predictions and resolved_candidates:
        resolved_candidates, active_model_version, pred_timestamp, ml_warnings = enrich_candidate_options_with_ml(
            candidate_options=resolved_candidates,
            config=cfg,
        )

    # 4. Pre-Solve Validation
    val_report = validate_optimization_inputs(
        candidate_options=resolved_candidates,
        products=resolved_products,
        config=cfg,
    )

    all_warnings = conversion_warnings + ml_warnings + val_report.warnings

    if not val_report.is_valid:
        diag = diagnose_infeasibility(resolved_candidates, resolved_products, cfg, val_report)
        elapsed = time.perf_counter() - start_time
        return OptimizationResult(
            status="INFEASIBLE",
            scenario_id=cfg.scenario_name,
            scenario_name=cfg.scenario_name,
            objective_value=None,
            currency=cfg.budget.currency,
            cost_breakdown={
                "procurement_cost": None,
                "shipping_cost": None,
                "inventory_cost": None,
                "delay_penalty": None,
                "risk_cost": None,
                "shortage_cost": None,
            },
            decisions=[],
            constraint_checks=[],
            warnings=val_report.errors + all_warnings,
            model_metadata={
                "solver": "PreSolveValidator",
                "model_version": active_model_version,
                "solve_time_seconds": round(elapsed, 4),
            },
            solver_name="PreSolveValidator",
            solve_time_seconds=round(elapsed, 4),
            objective=ObjectiveSummary(name=cfg.optimization.objective, total_cost=None, currency=cfg.budget.currency),
            constraints=constraint_summary,
            infeasibility_diagnostics=InfeasibilityReport(
                is_infeasible=True,
                conflicting_constraints=diag.conflicting_constraints,
                root_causes=val_report.errors + diag.root_causes,
                suggested_actions=diag.suggested_actions,
            ),
        )

    # 5. Build Problem
    try:
        problem, variables, objectives, registry = build_optimization_problem(
            candidate_options=resolved_candidates,
            products=resolved_products,
            config=cfg,
        )
    except Exception as build_exc:
        elapsed = time.perf_counter() - start_time
        logger.error("Failed to assemble mathematical optimization model: %s", build_exc)
        return OptimizationResult(
            status="ERROR",
            scenario_id=cfg.scenario_name,
            scenario_name=cfg.scenario_name,
            objective_value=None,
            currency=cfg.budget.currency,
            cost_breakdown={},
            decisions=[],
            constraint_checks=[],
            warnings=[f"Model assembly error: {build_exc}"],
            model_metadata={"solver": None, "model_version": active_model_version, "solve_time_seconds": round(elapsed, 4)},
            solver_name="PuLP_Builder",
            solve_time_seconds=round(elapsed, 4),
            objective=ObjectiveSummary(name=cfg.optimization.objective, total_cost=None, currency=cfg.budget.currency),
            constraints=constraint_summary,
        )

    # 6. Resolve Solver Engine
    solver = _resolve_pulp_solver(cfg)
    solver_name = type(solver).__name__ if solver else "NoneAvailable"

    if solver is None:
        elapsed = time.perf_counter() - start_time
        return OptimizationResult(
            status="ERROR",
            scenario_id=cfg.scenario_name,
            scenario_name=cfg.scenario_name,
            objective_value=None,
            currency=cfg.budget.currency,
            cost_breakdown={},
            decisions=[],
            constraint_checks=[],
            warnings=["No supported MILP solver available. Install highspy via 'pip install highspy'."],
            model_metadata={"solver": None, "model_version": active_model_version, "solve_time_seconds": round(elapsed, 4)},
            solver_name="NoneAvailable",
            solve_time_seconds=round(elapsed, 4),
            objective=ObjectiveSummary(name=cfg.optimization.objective, total_cost=None, currency=cfg.budget.currency),
            constraints=constraint_summary,
        )

    # 7. Execute Solve
    solve_start = time.perf_counter()
    try:
        solve_output = problem.solve(solver)
    except Exception as solver_exc:
        elapsed = time.perf_counter() - start_time
        logger.error("Solver execution threw exception: %s", solver_exc)
        return OptimizationResult(
            status="ERROR",
            scenario_id=cfg.scenario_name,
            scenario_name=cfg.scenario_name,
            objective_value=None,
            currency=cfg.budget.currency,
            cost_breakdown={},
            decisions=[],
            constraint_checks=[],
            warnings=[f"Solver runtime failure: {solver_exc}"],
            model_metadata={"solver": solver_name, "model_version": active_model_version, "solve_time_seconds": round(elapsed, 4)},
            solver_name=solver_name,
            solve_time_seconds=round(elapsed, 4),
            objective=ObjectiveSummary(name=cfg.optimization.objective, total_cost=None, currency=cfg.budget.currency),
            constraints=constraint_summary,
        )

    solve_duration = time.perf_counter() - solve_start
    elapsed = time.perf_counter() - start_time

    # 8. Inspect and Normalize Status
    raw_status = ""
    if hasattr(solve_output, "status_str"):
        raw_status = str(solve_output.status_str).upper()
    elif hasattr(problem, "status"):
        code_map = {1: "OPTIMAL", -1: "INFEASIBLE", -2: "UNBOUNDED", 0: "NOT_SOLVED"}
        raw_status = code_map.get(problem.status, "ERROR")
    else:
        raw_status = "OPTIMAL" if "optimal" in str(solve_output).lower() else "ERROR"

    if solve_duration >= cfg.optimization.time_limit_seconds and raw_status != "OPTIMAL":
        canonical_status = "TIME_LIMIT"
    elif "OPTIMAL" in raw_status:
        canonical_status = "OPTIMAL"
    elif "INFEASIBLE" in raw_status:
        canonical_status = "INFEASIBLE"
    elif "UNBOUNDED" in raw_status:
        canonical_status = "UNBOUNDED"
    else:
        canonical_status = "FEASIBLE" if "FEASIBLE" in raw_status else "ERROR"

    # Only report plans as valid if solver confirmed OPTIMAL or FEASIBLE
    if canonical_status not in ("OPTIMAL", "FEASIBLE"):
        diag = diagnose_infeasibility(resolved_candidates, resolved_products, cfg, val_report)
        return OptimizationResult(
            status=canonical_status,
            scenario_id=cfg.scenario_name,
            scenario_name=cfg.scenario_name,
            objective_value=None,
            currency=cfg.budget.currency,
            cost_breakdown={
                "procurement_cost": None,
                "shipping_cost": None,
                "inventory_cost": None,
                "delay_penalty": None,
                "risk_cost": None,
                "shortage_cost": None,
            },
            decisions=[],
            constraint_checks=[],
            warnings=all_warnings + [f"Solver concluded with status: {canonical_status} ({raw_status})"],
            model_metadata={
                "solver": solver_name,
                "model_version": active_model_version,
                "solve_time_seconds": round(elapsed, 4),
                "solver_duration_seconds": round(solve_duration, 4),
                "termination_reason": raw_status,
            },
            solver_name=solver_name,
            solve_time_seconds=round(elapsed, 4),
            objective=ObjectiveSummary(name=cfg.optimization.objective, total_cost=None, currency=cfg.budget.currency),
            constraints=constraint_summary,
            infeasibility_diagnostics=InfeasibilityReport(
                is_infeasible=True,
                conflicting_constraints=diag.conflicting_constraints,
                root_causes=diag.root_causes,
                suggested_actions=diag.suggested_actions,
            ),
        )

    # 9. Extract Decisions and Cost Components
    options_by_key = {
        (opt.supplier_id, opt.product_id, opt.transport_mode): opt
        for opt in resolved_candidates
    }

    decisions: List[DecisionAllocation] = []
    supplier_totals: Dict[str, float] = {s: 0.0 for s in variables.supplier_ids}

    for key, var in variables.q.items():
        val = float(var.value() or 0.0)
        if val > 1e-4:
            s_id, p_id, mode = key
            opt = options_by_key.get(key)
            if opt:
                proc_cost = val * opt.unit_cost
                ship_cost = val * opt.shipping_cost_per_unit
                del_cost = val * opt.expected_delay_cost_per_unit
                risk_rate = cfg.risk.operational_risk_cost_rate if (hasattr(cfg, "risk") and cfg.risk.enabled) else 0.0
                unit_risk = (
                    opt.expected_risk_cost_per_unit
                    if opt.expected_risk_cost_per_unit > 0
                    else (max(0.0, 1.0 - getattr(opt, "supplier_reliability", 1.0)) * risk_rate if risk_rate > 0 else 0.0)
                )
                risk_cost = val * unit_risk
                tot_item_cost = proc_cost + ship_cost + del_cost + risk_cost

                supplier_totals[s_id] = supplier_totals.get(s_id, 0.0) + val

                decisions.append(
                    DecisionAllocation(
                        supplier_id=opt.supplier_id,
                        supplier_name=opt.supplier_name,
                        product_id=opt.product_id,
                        product_name=opt.product_name,
                        transport_mode=opt.transport_mode,
                        quantity=round(val, 2),
                        unit_cost=opt.unit_cost,
                        shipping_cost_per_unit=opt.shipping_cost_per_unit,
                        expected_delay_days=opt.predicted_delay_days,
                        expected_delay_probability=opt.predicted_delay_probability,
                        predicted_delay=opt.predicted_delay_days,
                        total_procurement_cost=round(proc_cost, 2),
                        total_shipping_cost=round(ship_cost, 2),
                        expected_delay_cost=round(del_cost, 2),
                        expected_risk_cost=round(risk_cost, 2),
                        total_cost=round(tot_item_cost, 2),
                        estimated_cost=round(tot_item_cost, 2),
                    )
                )

    decisions.sort(key=lambda d: d.total_cost, reverse=True)

    # 10. Inventory Summary
    inventory_summary: List[InventoryResult] = []
    total_holding_cost = 0.0
    for prod in resolved_products:
        p_id = prod.product_id
        end_inv = float(variables.I[p_id].value() or 0.0)
        shortage = float(variables.u[p_id].value() or 0.0)
        procured = sum([d.quantity for d in decisions if d.product_id == p_id])
        h_cost = end_inv * prod.holding_cost_per_unit
        total_holding_cost += h_cost

        inventory_summary.append(
            InventoryResult(
                product_id=p_id,
                product_name=prod.product_name,
                starting_inventory=prod.starting_inventory,
                procured_quantity=round(procured, 2),
                demand=prod.demand,
                ending_inventory=round(end_inv, 2),
                shortage_quantity=round(shortage, 2),
                holding_cost=round(h_cost, 2),
            )
        )

    # 11. Cost Breakdown & Computed Objective
    tot_proc_cost = sum([d.total_procurement_cost for d in decisions])
    tot_ship_cost = sum([d.total_shipping_cost for d in decisions])
    tot_delay_cost = sum([d.expected_delay_cost for d in decisions])
    tot_risk_cost = sum([d.expected_risk_cost for d in decisions])
    tot_short_cost = sum([
        float(variables.u[p.product_id].value() or 0.0) * p.shortage_penalty_per_unit
        for p in resolved_products
    ])

    computed_total_cost = round(
        tot_proc_cost + tot_ship_cost + total_holding_cost + tot_delay_cost + tot_risk_cost + tot_short_cost,
        2,
    )

    cost_breakdown = {
        "procurement_cost": round(tot_proc_cost, 2),
        "shipping_cost": round(tot_ship_cost, 2),
        "inventory_cost": round(total_holding_cost, 2),
        "delay_penalty": round(tot_delay_cost, 2),
        "risk_cost": round(tot_risk_cost, 2),
        "shortage_cost": round(tot_short_cost, 2),
    }

    # 12. Supplier Capacity Utilization
    supplier_caps: Dict[str, float] = {}
    for opt in resolved_candidates:
        if opt.supplier_id not in supplier_caps:
            cap = (
                opt.supplier_capacity
                if cfg.supplier.use_individual_capacities and opt.supplier_capacity > 0
                else cfg.supplier.default_max_capacity_units
            )
            supplier_caps[opt.supplier_id] = float(cap)

    supplier_util: List[SupplierCapacityUtilization] = []
    for s_id, used_qty in supplier_totals.items():
        max_cap = supplier_caps.get(s_id, cfg.supplier.default_max_capacity_units)
        pct = (used_qty / max_cap * 100.0) if max_cap > 0 else 0.0
        supplier_util.append(
            SupplierCapacityUtilization(
                supplier_id=s_id,
                allocated_units=round(used_qty, 2),
                max_capacity_units=round(max_cap, 2),
                utilization_pct=round(pct, 2),
                remaining_capacity=round(max(0.0, max_cap - used_qty), 2),
            )
        )

    # 13. Constraint Audit & Slack Checks
    constraint_checks: List[ConstraintCheckResult] = []

    # Budget Check
    cash_spend = tot_proc_cost + tot_ship_cost + total_holding_cost
    if getattr(cfg.budget, "include_expected_delay_penalty", True):
        cash_spend += tot_delay_cost
    if getattr(cfg.budget, "include_risk_cost", False):
        cash_spend += tot_risk_cost

    budget_limit = cfg.budget.max_total_cost
    budget_slack = budget_limit - cash_spend
    budget_status = "BINDING" if abs(budget_slack) < 1.0 else ("SATISFIED" if budget_slack >= 0 else "VIOLATED")

    constraint_checks.append(
        ConstraintCheckResult(
            name="Constraint_Budget_Limit",
            category="Budget",
            status=budget_status,
            lhs_value=round(cash_spend, 2),
            rhs_value=round(budget_limit, 2),
            slack=round(budget_slack, 2),
            description=f"Budget utilization: {cash_spend:,.2f} / {budget_limit:,.2f} {cfg.budget.currency}",
        )
    )

    # Minimum Inventory Check
    total_ending_inv = sum([i.ending_inventory for i in inventory_summary])
    min_inv_req = cfg.inventory.minimum_required_units
    inv_slack = total_ending_inv - min_inv_req
    inv_status = "BINDING" if abs(inv_slack) < 1.0 else ("SATISFIED" if inv_slack >= 0 else "VIOLATED")

    constraint_checks.append(
        ConstraintCheckResult(
            name="Constraint_Minimum_Inventory_Aggregate",
            category="MinimumInventory",
            status=inv_status,
            lhs_value=round(total_ending_inv, 2),
            rhs_value=round(min_inv_req, 2),
            slack=round(inv_slack, 2),
            description=f"Aggregate ending inventory: {total_ending_inv:,.1f} / {min_inv_req:,.1f} units",
        )
    )

    # Supplier Capacity Checks
    for s_id, used_qty in supplier_totals.items():
        max_cap = supplier_caps.get(s_id, cfg.supplier.default_max_capacity_units)
        slack = max_cap - used_qty
        c_status = "BINDING" if abs(slack) < 1.0 else ("SATISFIED" if slack >= 0 else "VIOLATED")
        constraint_checks.append(
            ConstraintCheckResult(
                name=f"Constraint_Supplier_Capacity_{s_id}",
                category="SupplierCapacity",
                status=c_status,
                lhs_value=round(used_qty, 2),
                rhs_value=round(max_cap, 2),
                slack=round(slack, 2),
                description=f"Supplier {s_id} procurement: {used_qty:,.1f} / {max_cap:,.1f} units",
            )
        )

    budget_pct = (cash_spend / budget_limit * 100.0) if budget_limit > 0 else 0.0

    return OptimizationResult(
        status=canonical_status,
        scenario_id=cfg.scenario_name,
        scenario_name=cfg.scenario_name,
        objective_value=computed_total_cost,
        currency=cfg.budget.currency,
        cost_breakdown=cost_breakdown,
        decisions=decisions,
        constraint_checks=constraint_checks,
        warnings=all_warnings,
        model_metadata={
            "solver": solver_name,
            "model_version": active_model_version,
            "prediction_timestamp": pred_timestamp,
            "solve_time_seconds": round(elapsed, 4),
            "solver_duration_seconds": round(solve_duration, 4),
            "termination_reason": raw_status,
            "variable_count": len(problem.variables() if callable(problem.variables) else problem.variables),
            "constraint_count": len(registry.constraints),
        },
        solver_name=solver_name,
        solve_time_seconds=round(elapsed, 4),
        objective=ObjectiveSummary(
            name=cfg.optimization.objective,
            total_cost=computed_total_cost,
            currency=cfg.budget.currency,
            cost_breakdown={
                "procurement_cost": cost_breakdown["procurement_cost"],
                "shipping_cost": cost_breakdown["shipping_cost"],
                "holding_cost": cost_breakdown["inventory_cost"],
                "expected_delay_cost": cost_breakdown["delay_penalty"],
                "operational_risk_cost": cost_breakdown["risk_cost"],
                "shortage_penalty_cost": cost_breakdown["shortage_cost"],
            },
        ),
        constraints=constraint_summary,
        inventory_summary=inventory_summary,
        supplier_utilization=supplier_util,
        budget_utilization_pct=round(budget_pct, 2),
    )


def solve_optimization_problem(
    candidate_options: List[CandidateOption],
    products: List[ProductData],
    config: Optional[ScenarioConfig] = None,
) -> OptimizationResult:
    """
    Backwards-compatible wrapper calling solve_supply_chain.
    """
    return solve_supply_chain(
        candidate_options=candidate_options,
        product_data=products,
        scenario=config,
    )


def _convert_raw_inputs(
    suppliers: Optional[Any],
    products: Optional[Any],
    demand: Optional[Any],
    inventory: Optional[Any],
    shipping_options: Optional[Any],
    config: ScenarioConfig,
) -> Tuple[List[CandidateOption], List[ProductData], List[str]]:
    """
    Helper converting polymorphic raw supply-chain inputs (dicts, dataframes, models)
    into validated CandidateOption and ProductData instances.
    """
    warnings: List[str] = []
    prod_list: List[ProductData] = []
    cand_list: List[CandidateOption] = []

    if products is None:
        raise ValueError("Missing required 'products' input data.")

    # 1. Convert Products
    prod_items = products.to_dict(orient="records") if hasattr(products, "to_dict") else products
    if isinstance(prod_items, dict):
        prod_items = [prod_items]

    for p in prod_items:
        p_id = str(p.get("product_id") or p.get("id") or "")
        p_name = str(p.get("product_name") or p_id)
        unit_cost = float(p.get("unit_cost", 50.0))

        # Check inventory and demand maps if provided
        start_inv = 0.0
        if inventory is not None:
            if isinstance(inventory, dict):
                start_inv = float(inventory.get(p_id, 0.0))
            elif isinstance(inventory, (int, float)):
                start_inv = float(inventory)
        elif "starting_inventory" in p or "inventory_level" in p:
            start_inv = float(p.get("starting_inventory") or p.get("inventory_level", 0.0))

        req_demand = 0.0
        if demand is not None:
            if isinstance(demand, dict):
                req_demand = float(demand.get(p_id, 0.0))
            elif isinstance(demand, (int, float)):
                req_demand = float(demand)
        elif "demand" in p:
            req_demand = float(p.get("demand", 0.0))

        h_cost = float(p.get("holding_cost_per_unit", unit_cost * config.inventory.holding_cost_rate))
        s_cost = float(p.get("shortage_penalty_per_unit", unit_cost * config.inventory.shortage_penalty_rate))
        min_inv = float(p.get("minimum_inventory", 0.0))

        prod_list.append(
            ProductData(
                product_id=p_id,
                product_name=p_name,
                starting_inventory=start_inv,
                demand=req_demand,
                unit_cost=unit_cost,
                holding_cost_per_unit=h_cost,
                shortage_penalty_per_unit=s_cost,
                minimum_inventory=min_inv,
            )
        )

    # 2. Convert Shipping Options / Candidate Options
    if shipping_options is not None:
        ship_items = shipping_options.to_dict(orient="records") if hasattr(shipping_options, "to_dict") else shipping_options
        if isinstance(ship_items, dict):
            ship_items = [ship_items]

        for opt in ship_items:
            s_id = str(opt.get("supplier_id", "SUP001"))
            s_name = str(opt.get("supplier_name", s_id))
            p_id = str(opt.get("product_id", prod_list[0].product_id if prod_list else "P1"))
            p_name = str(opt.get("product_name", p_id))
            mode = str(opt.get("transport_mode", "Road"))
            u_cost = float(opt.get("unit_cost", 50.0))
            ship_cost = float(opt.get("shipping_cost_per_unit", 5.0))
            lead_time = float(opt.get("lead_time_days", 3.0))
            prob = float(opt.get("predicted_delay_probability", 0.10))
            pred_days = float(opt.get("predicted_delay_days", 0.5))
            cap = float(opt.get("supplier_capacity", config.supplier.default_max_capacity_units))
            rel = float(opt.get("supplier_reliability", 0.90))

            del_cost = float(opt.get("expected_delay_cost_per_unit", prob * (config.delivery.daily_delay_penalty * pred_days / 100.0)))
            risk_rate = config.risk.operational_risk_cost_rate if hasattr(config, "risk") else 0.0
            risk_cost = float(opt.get("expected_risk_cost_per_unit", max(0.0, 1.0 - rel) * risk_rate))

            cand_list.append(
                CandidateOption(
                    supplier_id=s_id,
                    supplier_name=s_name,
                    product_id=p_id,
                    product_name=p_name,
                    transport_mode=mode,
                    unit_cost=u_cost,
                    shipping_cost_per_unit=ship_cost,
                    lead_time_days=lead_time,
                    predicted_delay_probability=prob,
                    predicted_delay_days=pred_days,
                    expected_delay_cost_per_unit=del_cost,
                    supplier_capacity=cap,
                    supplier_reliability=rel,
                    expected_risk_cost_per_unit=risk_cost,
                )
            )

    return cand_list, prod_list, warnings
