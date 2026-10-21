"""
SupplyPrescript — Unit Tests: Alternative Evaluator & Solution Validation (Day 13 & 15)
======================================================================================
Tests independent mathematical validation, hard constraint audits (budget, capacity,
inventory, delivery), recommendation safety gating, and Day 12 objective evaluation.
"""

from __future__ import annotations

import pytest

from optimization.alternative_evaluator import (
    calculate_objective_cost,
    evaluate_alternatives,
    is_recommendation_eligible,
    validate_optimization_solution,
)
from optimization.config import BudgetConfig, DeliveryConfig, InventoryConfig, ScenarioConfig, get_baseline_scenario
from optimization.decision_schemas import (
    AlternativeOption,
    BaselineSummary,
    FeasibilityStatus,
    RiskLevel,
    SolutionValidationReport,
)


@pytest.fixture
def baseline_summary():
    return BaselineSummary(
        shipment_id="TEST-SHIP-01",
        product_id="PROD001",
        product_name="Controller",
        supplier_id="SUP001",
        supplier_name="Alpha",
        transport_mode="Road",
        quantity=100.0,
        unit_cost=50.0,
        shipping_cost=250.0,
        estimated_total_cost=5250.0,
        predicted_delay_probability=0.80,
        predicted_delay_days=8.0,
        risk_level="HIGH",
        planned_lead_time_days=5.0,
        total_delivery_days=13.0,
        currency="USD",
    )


def test_validate_solution_strictly_feasible():
    """Verify that a compliant candidate solution passes all 4 hard constraints."""
    config = get_baseline_scenario()  # Budget: $50,000, Max delay: 7.0 days

    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 15000.0,
        "quantity": 200.0,
        "supplier_capacity": 5000.0,
        "ending_inventory": 1500.0,
        "predicted_delay_days": 2.0,
    }

    report = validate_optimization_solution(sol, config)

    assert report.is_valid is True
    assert report.is_eligible_for_recommendation is True
    assert report.budget_passed is True
    assert report.capacity_passed is True
    assert report.inventory_passed is True
    assert report.delivery_passed is True
    assert len(report.violations) == 0
    # Positive slacks
    assert report.slacks["budget_slack"] == 35000.0
    assert report.slacks["capacity_slack"] == 4800.0
    assert report.slacks["inventory_slack"] == 500.0
    assert report.slacks["delay_slack"] == 5.0


def test_budget_constraint_violation_triggers_rejection():
    """Verify that a plan exceeding the configured budget ceiling is rejected."""
    config = get_baseline_scenario()  # Budget: $50,000

    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 50500.0,  # Exceeds $50,000
        "quantity": 100.0,
        "supplier_capacity": 5000.0,
        "ending_inventory": 1200.0,
        "predicted_delay_days": 1.0,
    }

    report = validate_optimization_solution(sol, config)

    assert report.is_valid is False
    assert report.budget_passed is False
    assert report.is_eligible_for_recommendation is False
    assert len(report.violations) >= 1
    assert any(v.constraint_name == "Maximum Budget" for v in report.violations)
    assert report.slacks["budget_slack"] < 0


def test_budget_at_exact_limit_accepted_within_tolerance():
    """Verify that a plan right at the budget limit is accepted within numerical tolerance."""
    config = get_baseline_scenario()  # Budget: $50,000

    # Exactly at limit + tiny floating point delta (1e-7)
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 50000.0 + 1e-7,
        "quantity": 100.0,
        "supplier_capacity": 5000.0,
        "ending_inventory": 1200.0,
        "predicted_delay_days": 1.0,
    }

    report = validate_optimization_solution(sol, config, tolerance=1e-6)
    assert report.budget_passed is True
    assert report.is_valid is True


def test_supplier_capacity_violation_triggers_rejection():
    """Verify that exceeding supplier capacity is detected and rejected."""
    config = get_baseline_scenario()

    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 10000.0,
        "quantity": 5500.0,  # Exceeds supplier capacity of 5,000
        "supplier_capacity": 5000.0,
        "ending_inventory": 2000.0,
        "predicted_delay_days": 1.0,
    }

    report = validate_optimization_solution(sol, config)

    assert report.is_valid is False
    assert report.capacity_passed is False
    assert any(v.constraint_name == "Supplier Capacity" for v in report.violations)


def test_delivery_delay_violation_triggers_rejection():
    """Verify that exceeding maximum acceptable delay days fails validation."""
    config = get_baseline_scenario()  # Max delay: 7.0 days

    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 10000.0,
        "quantity": 100.0,
        "predicted_delay_days": 8.5,  # Exceeds 7.0 days
    }

    report = validate_optimization_solution(sol, config)

    assert report.is_valid is False
    assert report.delivery_passed is False
    assert any(v.constraint_name == "Delivery Delay Tolerance" for v in report.violations)


def test_recommendation_safety_gate_fails_closed():
    """Verify that is_recommendation_eligible returns False on invalid reports or non-feasible status."""
    valid_report = SolutionValidationReport(
        is_valid=True,
        is_eligible_for_recommendation=True,
        budget_passed=True,
        capacity_passed=True,
        inventory_passed=True,
        delivery_passed=True,
    )
    invalid_report = SolutionValidationReport(
        is_valid=False,
        is_eligible_for_recommendation=False,
        budget_passed=False,
        capacity_passed=True,
        inventory_passed=True,
        delivery_passed=True,
    )

    opt_feasible = AlternativeOption(
        option_id="A",
        name="Air Freight",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=6000.0,
    )
    opt_infeasible = AlternativeOption(
        option_id="B",
        name="Secondary Supplier",
        feasibility=FeasibilityStatus.INFEASIBLE,
        estimated_total_cost=65000.0,
    )
    opt_insufficient = AlternativeOption(
        option_id="C",
        name="Delay Product Launch",
        feasibility=FeasibilityStatus.INSUFFICIENT_DATA,
    )

    # Valid + FEASIBLE -> Eligible
    assert is_recommendation_eligible(opt_feasible, valid_report) is True
    # Invalid report -> Not eligible
    assert is_recommendation_eligible(opt_feasible, invalid_report) is False
    # Infeasible option -> Not eligible even if report says valid
    assert is_recommendation_eligible(opt_infeasible, valid_report) is False
    # Insufficient data option -> Not eligible
    assert is_recommendation_eligible(opt_insufficient, valid_report) is False


def test_day_12_objective_cost_formulation():
    """Verify Day 12 objective formula: Z = C_total + C_delay + C_risk."""
    config = get_baseline_scenario()
    config.delivery.daily_delay_penalty = 25.0
    config.risk.operational_risk_cost_rate = 5.0
    config.risk.enabled = True

    opt = AlternativeOption(
        option_id="A",
        name="Air Freight",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=10000.0,
        predicted_delay_days=2.0,
        delay_probability=0.20,
        risk_level=RiskLevel.LOW,  # rel proxy 0.95 -> 1 - 0.95 = 0.05
    )

    # C_total = 10,000.0
    # C_delay = 25.0 * 2.0 * 0.20 = 10.0
    # C_risk = 5.0 * (1 - 0.95) * 100 = 5.0 * 0.05 * 100 = 25.0
    # Z = 10000 + 10 + 25 = 10035.0
    z = calculate_objective_cost(opt, config, quantity=100.0)
    assert z == 10035.0
