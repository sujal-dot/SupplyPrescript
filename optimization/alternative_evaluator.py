"""
SupplyPrescript — Alternative Decision Evaluator & Solution Validation Engine
=============================================================================
Evaluates prescriptive supply-chain alternatives against Day 12 multi-component objective:
    min Z = C_total + C_delay + C_risk

Provides independent mathematical validation and strict recommendation safety gating:
no infeasible, unverified, or constraint-violating option is ever presented as a recommendation.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union

from optimization.config import ScenarioConfig, get_baseline_scenario
from optimization.decision_schemas import (
    AlternativeOption,
    BaselineSummary,
    ConstraintViolation,
    FeasibilityStatus,
    SolutionValidationReport,
)

logger = logging.getLogger("optimization.alternative_evaluator")


def validate_optimization_solution(
    solution: Union[AlternativeOption, Dict[str, Any]],
    constraints: ScenarioConfig,
    tolerance: float = 1e-6,
) -> SolutionValidationReport:
    """
    Independent audit of an optimization solution against hard business constraints:
    1. Cash Budget: C_budgeted <= B_max + tolerance
    2. Supplier Capacity: q <= K_s + tolerance
    3. Minimum Inventory: I >= I_min - tolerance
    4. Delivery Delay: predicted_delay_days <= max_delay + tolerance

    Returns a comprehensive SolutionValidationReport with slacks and violation diagnostics.
    """
    violations: List[ConstraintViolation] = []
    slacks: Dict[str, float] = {}

    # Extract values whether solution is AlternativeOption or dict
    if isinstance(solution, AlternativeOption):
        sol_data = solution.model_dump()
    elif isinstance(solution, dict):
        sol_data = solution
    else:
        raise TypeError(f"Expected AlternativeOption or dict, got {type(solution).__name__}")

    feasibility_val = sol_data.get("feasibility")
    if hasattr(feasibility_val, "value"):
        feasibility_str = feasibility_val.value
    else:
        feasibility_str = str(feasibility_val or "UNKNOWN")

    # If status is already INSUFFICIENT_DATA or ERROR, it cannot pass validation
    if feasibility_str in ("INSUFFICIENT_DATA", "ERROR"):
        return SolutionValidationReport(
            is_valid=False,
            is_eligible_for_recommendation=False,
            budget_passed=False,
            capacity_passed=False,
            inventory_passed=False,
            delivery_passed=False,
            violations=[
                ConstraintViolation(
                    constraint_name="Data Sufficiency",
                    limit_value=1.0,
                    actual_value=0.0,
                    violation_amount=1.0,
                    message=f"Alternative cannot be verified due to status: {feasibility_str}",
                )
            ],
            slacks={},
        )

    # 1. Budget Constraint Audit: C_budgeted <= B_max
    budget_passed = True
    b_max = float(constraints.budget.max_total_cost)
    est_total_cost = sol_data.get("estimated_total_cost")

    cost_breakdown = sol_data.get("cost_breakdown") or {}
    proc_cost = float(cost_breakdown.get("procurement_cost") or 0.0)
    ship_cost = float(cost_breakdown.get("shipping_cost") or 0.0)
    delay_cost = float(cost_breakdown.get("delay_cost") or 0.0)
    risk_cost = float(cost_breakdown.get("risk_cost") or 0.0)

    # Missing or invalid cost check
    if est_total_cost is None and not cost_breakdown:
        budget_passed = False
        violations.append(
            ConstraintViolation(
                constraint_name="Maximum Budget",
                limit_value=b_max,
                actual_value=-1.0,
                violation_amount=b_max,
                message="Cost data is missing; candidate solution cannot be verified as budget-compliant.",
            )
        )
    else:
        try:
            if est_total_cost is not None:
                budgeted_cost = float(est_total_cost)
                if constraints.budget.include_expected_delay_penalty and delay_cost > 0:
                    if "delay_cost" not in str(sol_data.get("cost_breakdown_included", "")):
                        budgeted_cost += delay_cost
            else:
                budgeted_cost = proc_cost + ship_cost
                if constraints.budget.include_expected_delay_penalty:
                    budgeted_cost += delay_cost

            if math.isnan(budgeted_cost) or math.isinf(budgeted_cost) or budgeted_cost < 0:
                budget_passed = False
                violations.append(
                    ConstraintViolation(
                        constraint_name="Maximum Budget",
                        limit_value=b_max,
                        actual_value=float("nan") if math.isnan(budgeted_cost) else budgeted_cost,
                        violation_amount=b_max,
                        message=f"Cost value ({budgeted_cost}) is invalid or non-finite.",
                    )
                )
            else:
                budget_slack = b_max - budgeted_cost
                slacks["budget_slack"] = round(budget_slack, 2)

                if budgeted_cost > b_max + tolerance:
                    budget_passed = False
                    v_amount = round(budgeted_cost - b_max, 2)
                    violations.append(
                        ConstraintViolation(
                            constraint_name="Maximum Budget",
                            limit_value=b_max,
                            actual_value=round(budgeted_cost, 2),
                            violation_amount=v_amount,
                            message=(
                                f"Applicable expenditure ${budgeted_cost:,.2f} exceeds configured budget limit "
                                f"${b_max:,.2f} by ${v_amount:,.2f}."
                            ),
                        )
                    )
        except (ValueError, TypeError) as exc:
            budget_passed = False
            violations.append(
                ConstraintViolation(
                    constraint_name="Maximum Budget",
                    limit_value=b_max,
                    actual_value=-1.0,
                    violation_amount=b_max,
                    message=f"Cost value could not be evaluated: {exc}",
                )
            )

    # 2. Supplier Capacity Constraint Audit: sum_{p,m} q <= K_s
    capacity_passed = True
    allocations = sol_data.get("allocations")
    if allocations and isinstance(allocations, list):
        quantity = sum(float(a.get("quantity", 0.0)) for a in allocations)
    else:
        raw_qty = sol_data.get("quantity") or sol_data.get("allocated_quantity")
        quantity = float(raw_qty) if raw_qty is not None else 0.0

    supplier_capacity = sol_data.get("supplier_capacity")
    if supplier_capacity is not None:
        try:
            k_s = float(supplier_capacity)
            if math.isnan(k_s) or math.isinf(k_s) or k_s < 0:
                capacity_passed = False
                violations.append(
                    ConstraintViolation(
                        constraint_name="Supplier Capacity",
                        limit_value=0.0,
                        actual_value=k_s,
                        violation_amount=1.0,
                        message=f"Supplier capacity ({k_s}) is invalid or negative.",
                    )
                )
            elif math.isnan(quantity) or math.isinf(quantity) or quantity < 0:
                capacity_passed = False
                violations.append(
                    ConstraintViolation(
                        constraint_name="Supplier Capacity",
                        limit_value=k_s,
                        actual_value=quantity,
                        violation_amount=1.0,
                        message=f"Order quantity ({quantity}) is invalid or negative.",
                    )
                )
            else:
                cap_slack = k_s - quantity
                slacks["capacity_slack"] = round(cap_slack, 2)
                if quantity > k_s + tolerance:
                    capacity_passed = False
                    v_amount = round(quantity - k_s, 2)
                    violations.append(
                        ConstraintViolation(
                            constraint_name="Supplier Capacity",
                            limit_value=k_s,
                            actual_value=quantity,
                            violation_amount=v_amount,
                            message=f"Order volume of {quantity:,.0f} units exceeds maximum supplier capacity of {k_s:,.0f} units.",
                        )
                    )
        except (ValueError, TypeError) as exc:
            capacity_passed = False
            violations.append(
                ConstraintViolation(
                    constraint_name="Supplier Capacity",
                    limit_value=0.0,
                    actual_value=-1.0,
                    violation_amount=1.0,
                    message=f"Supplier capacity could not be evaluated: {exc}",
                )
            )

    # 3. Minimum Inventory Constraint Audit: I >= I_min
    inventory_passed = True
    ending_inventory = sol_data.get("ending_inventory")
    i_min = float(constraints.inventory.minimum_required_units)

    # Calculate ending inventory from flow conservation if initial & demand are provided
    starting_inv = sol_data.get("starting_inventory") or sol_data.get("initial_inventory")
    demand = sol_data.get("demand")
    procurement = sol_data.get("procurement_quantity") or quantity

    if ending_inventory is None and starting_inv is not None and demand is not None:
        try:
            ending_inventory = float(starting_inv) + float(procurement or 0.0) - float(demand)
        except (ValueError, TypeError):
            pass

    if ending_inventory is not None:
        try:
            ending_inv_val = float(ending_inventory)
            if math.isnan(ending_inv_val) or math.isinf(ending_inv_val):
                inventory_passed = False
                violations.append(
                    ConstraintViolation(
                        constraint_name="Minimum Inventory Target",
                        limit_value=i_min,
                        actual_value=ending_inv_val,
                        violation_amount=i_min,
                        message=f"Ending inventory value ({ending_inv_val}) is non-finite.",
                    )
                )
            else:
                inv_slack = ending_inv_val - i_min
                slacks["inventory_slack"] = round(inv_slack, 2)
                if ending_inv_val < i_min - tolerance:
                    inventory_passed = False
                    v_amount = round(i_min - ending_inv_val, 2)
                    violations.append(
                        ConstraintViolation(
                            constraint_name="Minimum Inventory Target",
                            limit_value=i_min,
                            actual_value=ending_inv_val,
                            violation_amount=v_amount,
                            message=f"Ending inventory of {ending_inv_val:,.0f} units falls below safety threshold of {i_min:,.0f} units.",
                        )
                    )
        except (ValueError, TypeError) as exc:
            inventory_passed = False
            violations.append(
                ConstraintViolation(
                    constraint_name="Minimum Inventory Target",
                    limit_value=i_min,
                    actual_value=-1.0,
                    violation_amount=i_min,
                    message=f"Inventory could not be evaluated: {exc}",
                )
            )

    # 4. Delivery Delay Tolerance Audit: delay_days <= max_delay
    delivery_passed = True
    predicted_delay = sol_data.get("predicted_delay_days")
    max_acceptable_delay = float(constraints.delivery.maximum_acceptable_delay_days)

    if predicted_delay is not None:
        try:
            delay_val = float(predicted_delay)
            if math.isnan(delay_val) or math.isinf(delay_val) or delay_val < 0:
                delivery_passed = False
                violations.append(
                    ConstraintViolation(
                        constraint_name="Delivery Delay Tolerance",
                        limit_value=max_acceptable_delay,
                        actual_value=delay_val,
                        violation_amount=max_acceptable_delay,
                        message=f"Predicted delay ({delay_val}) is invalid or non-finite.",
                    )
                )
            else:
                delay_slack = max_acceptable_delay - delay_val
                slacks["delay_slack"] = round(delay_slack, 2)
                if delay_val > max_acceptable_delay + tolerance:
                    delivery_passed = False
                    v_amount = round(delay_val - max_acceptable_delay, 2)
                    violations.append(
                        ConstraintViolation(
                            constraint_name="Delivery Delay Tolerance",
                            limit_value=max_acceptable_delay,
                            actual_value=delay_val,
                            violation_amount=v_amount,
                            message=f"Predicted delay of {delay_val:.1f} days exceeds allowable tolerance of {max_acceptable_delay:.1f} days.",
                        )
                    )
        except (ValueError, TypeError) as exc:
            delivery_passed = False
            violations.append(
                ConstraintViolation(
                    constraint_name="Delivery Delay Tolerance",
                    limit_value=max_acceptable_delay,
                    actual_value=-1.0,
                    violation_amount=max_acceptable_delay,
                    message=f"Delivery delay could not be evaluated: {exc}",
                )
            )

    is_valid = len(violations) == 0
    is_eligible = is_valid and (feasibility_str == "FEASIBLE")

    return SolutionValidationReport(
        is_valid=is_valid,
        is_eligible_for_recommendation=is_eligible,
        budget_passed=budget_passed,
        capacity_passed=capacity_passed,
        inventory_passed=inventory_passed,
        delivery_passed=delivery_passed,
        violations=violations,
        slacks=slacks,
    )


def is_recommendation_eligible(
    solution: Union[AlternativeOption, Dict[str, Any]],
    validation_report: SolutionValidationReport,
) -> bool:
    """
    Recommendation safety gate.
    Returns True IF AND ONLY IF:
    - Solution is strictly FEASIBLE.
    - Independent mathematical validation report confirms zero constraint violations.
    - All business constraints (budget, capacity, inventory, delivery) pass.
    """
    if not validation_report.is_valid:
        return False

    feasibility = getattr(solution, "feasibility", None)
    if hasattr(feasibility, "value"):
        feasibility_str = feasibility.value
    elif isinstance(solution, dict):
        f = solution.get("feasibility")
        feasibility_str = f.value if hasattr(f, "value") else str(f or "")
    else:
        feasibility_str = str(feasibility or "")

    if feasibility_str != FeasibilityStatus.FEASIBLE.value:
        return False

    return validation_report.is_eligible_for_recommendation


def calculate_objective_cost(
    option: AlternativeOption,
    config: ScenarioConfig,
    quantity: float = 100.0,
) -> float:
    """
    Calculate Day 12 Prescriptive Objective Cost:
        min Z = C_total + C_delay + C_risk
    Where:
        C_total = Procurement + Shipping + Shortage
        C_delay = daily_delay_penalty * predicted_delay_days * delay_probability
        C_risk  = operational_risk_cost_rate * (1 - supplier_reliability) * quantity
    """
    c_total = option.estimated_total_cost or 0.0
    delay_prob = option.delay_probability or 0.0
    delay_days = option.predicted_delay_days or 0.0

    c_delay = round(config.delivery.daily_delay_penalty * delay_days * delay_prob, 2)

    risk_rate = config.risk.operational_risk_cost_rate if config.risk.enabled else 0.0
    # Reliability proxy based on risk level
    rel = 0.95 if option.risk_level == "LOW" else (0.80 if option.risk_level == "MEDIUM" else 0.60)
    c_risk = round(risk_rate * (1.0 - rel) * quantity, 2)

    return round(c_total + c_delay + c_risk, 2)


def evaluate_alternatives(
    baseline: BaselineSummary,
    alternatives: List[AlternativeOption],
    config: ScenarioConfig,
) -> Tuple[List[AlternativeOption], Dict[str, SolutionValidationReport]]:
    """
    Audit each alternative against hard constraints and evaluate its Day 12 objective score.
    Returns updated list of alternatives and their validation reports.
    """
    audited_options: List[AlternativeOption] = []
    reports: Dict[str, SolutionValidationReport] = {}

    for opt in alternatives:
        report = validate_optimization_solution(opt, config)
        reports[opt.option_id] = report

        # Update feasibility and violations if independent validation failed
        updated_opt = opt.model_copy(deep=True)
        if not report.is_valid:
            if updated_opt.feasibility == FeasibilityStatus.FEASIBLE:
                updated_opt.feasibility = FeasibilityStatus.INFEASIBLE
            # Append new violations if not already present
            existing_names = {v.constraint_name for v in updated_opt.constraint_violations}
            for v in report.violations:
                if v.constraint_name not in existing_names:
                    updated_opt.constraint_violations.append(v)

        if updated_opt.objective_value is None and updated_opt.estimated_total_cost is not None:
            updated_opt.objective_value = calculate_objective_cost(updated_opt, config, baseline.quantity)

        audited_options.append(updated_opt)

    return audited_options, reports
