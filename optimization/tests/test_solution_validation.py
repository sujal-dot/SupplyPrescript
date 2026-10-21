"""
SupplyPrescript — Hard Constraint Audit Suite: Solution Validation (Day 15)
==========================================================================
Verifies that validate_optimization_solution performs an independent audit
of candidate solutions across all hard business constraints.
"""

from __future__ import annotations

import pytest

from optimization.alternative_evaluator import validate_optimization_solution
from optimization.config import get_baseline_scenario
from optimization.decision_schemas import AlternativeOption, FeasibilityStatus


def test_independent_audit_multiple_simultaneous_violations():
    """Verify that multiple simultaneous violations are accurately detected and reported."""
    config = get_baseline_scenario()  # Budget: $50,000, Max delay: 7.0 days, Default capacity: 5,000

    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 55000.0,  # Exceeds budget
        "quantity": 6000.0,  # Exceeds capacity
        "supplier_capacity": 5000.0,
        "ending_inventory": 800.0,  # Below 1,000 min inventory
        "predicted_delay_days": 10.0,  # Exceeds 7.0 days max delay
    }

    report = validate_optimization_solution(sol, config)

    assert report.is_valid is False
    assert report.budget_passed is False
    assert report.capacity_passed is False
    assert report.inventory_passed is False
    assert report.delivery_passed is False

    assert len(report.violations) == 4
    violation_names = {v.constraint_name for v in report.violations}
    assert "Maximum Budget" in violation_names
    assert "Supplier Capacity" in violation_names
    assert "Minimum Inventory Target" in violation_names
    assert "Delivery Delay Tolerance" in violation_names


def test_independent_audit_accepts_alternative_option_instance():
    """Verify that validate_optimization_solution accepts Pydantic AlternativeOption directly."""
    config = get_baseline_scenario()
    opt = AlternativeOption(
        option_id="A",
        name="Air Freight",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=25000.0,
        predicted_delay_days=1.5,
    )
    report = validate_optimization_solution(opt, config)
    assert report.is_valid is True
    assert report.budget_passed is True
    assert report.delivery_passed is True


def test_insufficient_data_status_fails_validation():
    """Verify that solutions with INSUFFICIENT_DATA status cannot pass validation."""
    config = get_baseline_scenario()
    opt = AlternativeOption(
        option_id="C",
        name="Delay Product Launch",
        feasibility=FeasibilityStatus.INSUFFICIENT_DATA,
    )
    report = validate_optimization_solution(opt, config)
    assert report.is_valid is False
    assert report.is_eligible_for_recommendation is False
