"""
SupplyPrescript — Hard Constraint Audit Suite: Budget Constraint (Day 15)
========================================================================
Audits the mathematical enforcement of the cash budget ceiling:
    C_budgeted <= B_max

Audits all 12 mandatory budget audit conditions:
1. A feasible plan whose budgeted cost is below the limit is accepted.
2. A plan exactly at the limit is accepted, subject to the defined numerical tolerance.
3. A plan exceeding the limit is rejected.
4. A plan whose procurement cost alone exceeds the limit is rejected.
5. A plan whose procurement plus shipping costs exceed the limit is rejected.
6. A plan whose total applicable costs exceed the limit is rejected even if its individual cost components are each below the limit.
7. A cheaper alternative is not selected if its budgeted cost exceeds the limit.
8. An infeasible solver result never becomes a recommendation.
9. A solver result with missing or invalid cost data is not treated as budget-compliant.
10. A budget changed through a valid scenario is enforced using the new configured limit.
11. A client request cannot bypass the trusted budget configuration by supplying an arbitrary higher budget.
12. A rounding or floating-point difference cannot cause an over-budget recommendation.

Critical Invariant:
For every option returned with a recommendation-eligible status:
    assert budgeted_cost <= max_budget + tolerance
"""

from __future__ import annotations

import math
import pytest

from optimization.alternative_evaluator import (
    calculate_objective_cost,
    is_recommendation_eligible,
    validate_optimization_solution,
)
from optimization.config import BudgetConfig, ScenarioConfig, get_baseline_scenario
from optimization.scenarios import get_budget_constrained_scenario
from optimization.decision_ranker import rank_alternatives
from optimization.decision_schemas import (
    AlternativeOption,
    BaselineSummary,
    ConstraintViolation,
    FeasibilityStatus,
    RecommendationStatus,
    RiskLevel,
    SolutionValidationReport,
)


@pytest.fixture
def baseline_summary():
    return BaselineSummary(
        shipment_id="TEST-BUDGET-SHIP-01",
        product_id="PROD001",
        product_name="Power Supply Unit",
        supplier_id="SUP001",
        supplier_name="Alpha Power",
        transport_mode="Road",
        quantity=100.0,
        unit_cost=50.0,
        shipping_cost=200.0,
        estimated_total_cost=5200.0,
        predicted_delay_probability=0.20,
        predicted_delay_days=1.0,
        risk_level="LOW",
        planned_lead_time_days=4.0,
        total_delivery_days=5.0,
        currency="USD",
    )


# 1. A feasible plan whose budgeted cost is below the limit is accepted
def test_1_feasible_plan_below_budget_is_accepted():
    config = get_baseline_scenario()  # Budget: $50,000 USD
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 35000.0,
        "quantity": 100.0,
        "supplier_capacity": 5000.0,
    }
    report = validate_optimization_solution(sol, config)
    assert report.is_valid is True
    assert report.budget_passed is True
    assert report.is_eligible_for_recommendation is True
    assert report.slacks["budget_slack"] == 15000.0


# 2. A plan exactly at the limit is accepted, subject to the defined numerical tolerance
def test_2_plan_at_exact_limit_accepted_within_tolerance():
    config = get_baseline_scenario()  # Budget: $50,000.0 USD
    tol = 1e-6
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 50000.0 + (tol / 2.0),
        "quantity": 100.0,
    }
    report = validate_optimization_solution(sol, config, tolerance=tol)
    assert report.budget_passed is True
    assert report.is_valid is True
    assert report.is_eligible_for_recommendation is True


# 3. A plan exceeding the limit is rejected
def test_3_plan_exceeding_budget_is_rejected():
    config = get_baseline_scenario()  # Budget: $50,000.0 USD
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 50001.0,
        "quantity": 100.0,
    }
    report = validate_optimization_solution(sol, config, tolerance=1e-6)
    assert report.budget_passed is False
    assert report.is_valid is False
    assert report.is_eligible_for_recommendation is False
    assert any(v.constraint_name == "Maximum Budget" for v in report.violations)


# 4. A plan whose procurement cost alone exceeds the limit is rejected
def test_4_plan_procurement_alone_exceeds_budget_rejected():
    config = get_baseline_scenario()  # Budget: $50,000 USD
    # Procurement alone = $60,000 (1200 units * $50)
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 62500.0,
        "cost_breakdown": {
            "procurement_cost": 60000.0,
            "shipping_cost": 2500.0,
        },
        "quantity": 1200.0,
    }
    report = validate_optimization_solution(sol, config)
    assert report.budget_passed is False
    assert report.is_valid is False
    assert report.is_eligible_for_recommendation is False


# 5. A plan whose procurement plus shipping costs exceed the limit is rejected
def test_5_procurement_plus_shipping_exceeds_budget_rejected():
    config = get_baseline_scenario()  # Budget: $50,000 USD
    # Procurement: $45,000, Shipping: $8,000 -> Total: $53,000
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 53000.0,
        "cost_breakdown": {
            "procurement_cost": 45000.0,
            "shipping_cost": 8000.0,
        },
        "quantity": 900.0,
    }
    report = validate_optimization_solution(sol, config)
    assert report.budget_passed is False
    assert report.is_valid is False
    assert report.is_eligible_for_recommendation is False


# 6. A plan whose total applicable costs exceed the limit is rejected even if its individual cost components are each below the limit
def test_6_total_applicable_cost_exceeds_limit_rejected():
    config = get_baseline_scenario()  # Budget: $50,000 USD
    # Procurement: $30,000, Shipping: $15,000, Delay penalty: $6,000 -> Total = $51,000
    # Each component (<$30k) is below $50k, but the sum exceeds $50k
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 45000.0,
        "cost_breakdown": {
            "procurement_cost": 30000.0,
            "shipping_cost": 15000.0,
            "delay_cost": 6000.0,
        },
        "quantity": 500.0,
    }
    report = validate_optimization_solution(sol, config)
    assert report.budget_passed is False
    assert report.is_valid is False
    assert report.slacks["budget_slack"] == -1000.0


# 7. A cheaper alternative is not selected if its budgeted cost exceeds the limit
def test_7_cheaper_alternative_not_selected_if_budget_exceeded(baseline_summary):
    # Tight scenario with $25,000 budget
    config = get_baseline_scenario()
    config.budget.max_total_cost = 25000.0

    # Option A has a lower objective value (28,000 vs 35,000) but costs $28,000 which EXCEEDS $25k budget
    opt_a_overbudget = AlternativeOption(
        option_id="A",
        name="Air Freight (Overbudget)",
        feasibility=FeasibilityStatus.INFEASIBLE,
        estimated_total_cost=28000.0,
        objective_value=28000.0,
        constraint_violations=[
            ConstraintViolation(
                constraint_name="Maximum Budget",
                limit_value=25000.0,
                actual_value=28000.0,
                violation_amount=3000.0,
                message="Cost exceeds budget",
            )
        ],
    )
    # Option B is more expensive in objective score (35,000) but its cost $20,000 is WITHIN $25k budget
    opt_b_feasible = AlternativeOption(
        option_id="B",
        name="Secondary Supplier (Feasible)",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=20000.0,
        objective_value=35000.0,
    )

    ranked, winner_id, status, reason, _ = rank_alternatives(
        alternatives=[opt_a_overbudget, opt_b_feasible],
        baseline=baseline_summary,
        config=config,
    )

    # Option A must NOT be selected despite lower objective; Option B must win
    assert status == RecommendationStatus.FEASIBLE_RECOMMENDATION
    assert winner_id == "B"
    assert next(o for o in ranked if o.option_id == "A").is_recommended is False
    assert next(o for o in ranked if o.option_id == "B").is_recommended is True


# 8. An infeasible solver result never becomes a recommendation
def test_8_infeasible_solver_result_never_becomes_recommendation(baseline_summary):
    config = get_baseline_scenario()

    opt_infeasible = AlternativeOption(
        option_id="A",
        name="Infeasible Candidate",
        feasibility=FeasibilityStatus.INFEASIBLE,
        estimated_total_cost=40000.0,
        objective_value=40000.0,
        constraint_violations=[
            ConstraintViolation(
                constraint_name="Maximum Budget",
                limit_value=50000.0,
                actual_value=55000.0,
                violation_amount=5000.0,
                message="Solver reported infeasibility",
            )
        ],
    )

    ranked, winner_id, status, reason, _ = rank_alternatives(
        alternatives=[opt_infeasible],
        baseline=baseline_summary,
        config=config,
    )

    assert status == RecommendationStatus.NO_FEASIBLE_OPTION
    assert winner_id is None
    assert opt_infeasible.is_recommended is False


# 9. A solver result with missing or invalid cost data is not treated as budget-compliant
def test_9_missing_or_invalid_cost_data_not_budget_compliant():
    config = get_baseline_scenario()

    # Case A: Missing cost data (None with no breakdown)
    sol_missing = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": None,
        "cost_breakdown": {},
    }
    report_missing = validate_optimization_solution(sol_missing, config)
    assert report_missing.budget_passed is False
    assert report_missing.is_valid is False
    assert report_missing.is_eligible_for_recommendation is False

    # Case B: NaN cost
    sol_nan = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": float("nan"),
    }
    report_nan = validate_optimization_solution(sol_nan, config)
    assert report_nan.budget_passed is False
    assert report_nan.is_valid is False

    # Case C: Negative cost
    sol_negative = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": -500.0,
    }
    report_negative = validate_optimization_solution(sol_negative, config)
    assert report_negative.budget_passed is False
    assert report_negative.is_valid is False


# 10. A budget changed through a valid scenario is enforced using the new configured limit
def test_10_budget_changed_through_valid_scenario_enforced():
    baseline_cfg = get_baseline_scenario()  # $50,000 USD
    constrained_cfg = get_budget_constrained_scenario(budget=30000.0)  # $30,000 USD

    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 38000.0,
        "quantity": 100.0,
    }

    # Feasible under baseline
    report_base = validate_optimization_solution(sol, baseline_cfg)
    assert report_base.budget_passed is True
    assert report_base.is_valid is True

    # Infeasible under budget_constrained
    report_constrained = validate_optimization_solution(sol, constrained_cfg)
    assert report_constrained.budget_passed is False
    assert report_constrained.is_valid is False
    assert report_constrained.slacks["budget_slack"] < 0


# 11. A client request cannot bypass the trusted budget configuration by supplying an arbitrary higher budget
def test_11_client_request_cannot_bypass_trusted_budget(baseline_summary):
    trusted_config = get_baseline_scenario()  # Trusted budget is $50,000 USD

    # Suppose an untrusted payload proposes a solution costing $75,000 claiming an arbitrary budget of $100,000
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 75000.0,
        "client_untrusted_budget": 100000.0,  # Ignored by trusted evaluator
    }

    # Evaluator MUST use trusted_config.budget.max_total_cost ($50,000), NOT client value
    report = validate_optimization_solution(sol, trusted_config)
    assert report.budget_passed is False
    assert report.is_valid is False
    assert report.violations[0].limit_value == 50000.0
    assert report.violations[0].actual_value == 75000.0


# 12. A rounding or floating-point difference cannot cause an over-budget recommendation
def test_12_rounding_or_floating_point_cannot_cause_over_budget_recommendation():
    config = get_baseline_scenario()  # Budget: $50,000.00 USD
    tol = 1e-6

    # Actual cost exceeds budget by slightly more than tolerance: $50,000.0001
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 50000.0001,
        "quantity": 100.0,
    }

    report = validate_optimization_solution(sol, config, tolerance=tol)
    assert report.budget_passed is False
    assert report.is_valid is False
    assert report.is_eligible_for_recommendation is False


# Critical Invariant: assert budgeted_cost <= max_budget + tolerance
def test_critical_invariant_recommendation_eligible_must_respect_budget(baseline_summary):
    config = get_baseline_scenario()
    tol = 1e-6
    max_b = config.budget.max_total_cost

    candidate_options = [
        AlternativeOption(option_id="A", name="Air", feasibility=FeasibilityStatus.FEASIBLE, estimated_total_cost=25000.0),
        AlternativeOption(option_id="B", name="Secondary", feasibility=FeasibilityStatus.FEASIBLE, estimated_total_cost=49999.99),
        AlternativeOption(option_id="C", name="Overbudget", feasibility=FeasibilityStatus.FEASIBLE, estimated_total_cost=50000.05),
    ]

    for opt in candidate_options:
        report = validate_optimization_solution(opt, config, tolerance=tol)
        is_eligible = is_recommendation_eligible(opt, report)
        if is_eligible:
            assert opt.estimated_total_cost <= max_b + tol, (
                f"INVARIANT VIOLATION: Option {opt.option_id} marked recommendation-eligible "
                f"with cost ${opt.estimated_total_cost} exceeding budget limit ${max_b}."
            )
        else:
            if opt.estimated_total_cost > max_b + tol:
                assert report.budget_passed is False
