"""
SupplyPrescript — Hard Constraint Audit Suite: Supplier Capacity Constraint (Day 15)
====================================================================================
Audits mathematical enforcement of supplier capacity limits:
    sum_{p, m} q_{s, p, m} <= K_s

Audits all mandatory supplier-capacity conditions:
1. A supplier allocation below capacity is accepted.
2. An allocation exactly at capacity is accepted.
3. An allocation above capacity is rejected.
4. Allocations across multiple products are aggregated correctly.
5. Multiple shipment or transport allocations cannot collectively exceed supplier available capacity.
6. Supplier-specific capacities are applied correctly.
7. Missing or invalid capacity is handled according to an explicit validation policy, not silently replaced with unlimited capacity.
8. A secondary supplier alternative is rejected if it exceeds that supplier's capacity.
"""

from __future__ import annotations

import pytest

from optimization.alternative_evaluator import is_recommendation_eligible, validate_optimization_solution
from optimization.config import get_baseline_scenario
from optimization.decision_ranker import rank_alternatives
from optimization.decision_schemas import (
    AlternativeOption,
    BaselineSummary,
    ConstraintViolation,
    FeasibilityStatus,
    RecommendationStatus,
)


@pytest.fixture
def baseline_summary():
    return BaselineSummary(
        shipment_id="TEST-CAP-SHIP-01",
        product_id="PROD001",
        product_name="Component",
        supplier_id="SUP001",
        supplier_name="Alpha",
        transport_mode="Road",
        quantity=100.0,
        unit_cost=50.0,
        shipping_cost=200.0,
        estimated_total_cost=5200.0,
        currency="USD",
    )


# 1. A supplier allocation below capacity is accepted
def test_supplier_capacity_satisfied():
    config = get_baseline_scenario()
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 20000.0,
        "quantity": 3200.0,
        "supplier_capacity": 5000.0,
    }
    report = validate_optimization_solution(sol, config)
    assert report.is_valid is True
    assert report.capacity_passed is True
    assert report.is_eligible_for_recommendation is True
    assert report.slacks["capacity_slack"] == 1800.0


# 2. An allocation exactly at capacity is accepted
def test_supplier_capacity_exact_limit_accepted():
    config = get_baseline_scenario()
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 20000.0,
        "quantity": 5000.0,
        "supplier_capacity": 5000.0,
    }
    report = validate_optimization_solution(sol, config, tolerance=1e-6)
    assert report.is_valid is True
    assert report.capacity_passed is True
    assert report.slacks["capacity_slack"] == 0.0


# 3. An allocation above capacity is rejected
def test_supplier_capacity_exceeded_rejected():
    config = get_baseline_scenario()
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 20000.0,
        "quantity": 5200.0,  # Exceeds 5,000 capacity
        "supplier_capacity": 5000.0,
    }
    report = validate_optimization_solution(sol, config)
    assert report.is_valid is False
    assert report.capacity_passed is False
    assert any(v.constraint_name == "Supplier Capacity" for v in report.violations)
    assert report.slacks["capacity_slack"] == -200.0


# 4. Allocations across multiple products are aggregated correctly
def test_allocations_across_multiple_products_aggregated():
    config = get_baseline_scenario()
    # Supplier capacity: 4,000 units
    # Product 1: 2,500 units, Product 2: 2,000 units -> Total = 4,500 units (Exceeds capacity)
    sol_multi_exceeded = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 30000.0,
        "supplier_capacity": 4000.0,
        "allocations": [
            {"product_id": "P1", "quantity": 2500.0},
            {"product_id": "P2", "quantity": 2000.0},
        ],
    }
    report = validate_optimization_solution(sol_multi_exceeded, config)
    assert report.capacity_passed is False
    assert report.is_valid is False
    assert report.slacks["capacity_slack"] == -500.0


# 5. Multiple shipment or transport allocations cannot collectively exceed supplier capacity
def test_multiple_transport_allocations_collectively_capped():
    config = get_baseline_scenario()
    # Air mode: 1,500 units, Road mode: 1,000 units -> Total = 2,500 units (Within 3,000 capacity)
    sol_transport_pass = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 25000.0,
        "supplier_capacity": 3000.0,
        "allocations": [
            {"mode": "Air", "quantity": 1500.0},
            {"mode": "Road", "quantity": 1000.0},
        ],
    }
    report = validate_optimization_solution(sol_transport_pass, config)
    assert report.capacity_passed is True
    assert report.slacks["capacity_slack"] == 500.0


# 6. Supplier-specific capacities are applied correctly
def test_supplier_specific_capacities_applied():
    config = get_baseline_scenario()
    # Small supplier with 800 units capacity
    sol_small = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 10000.0,
        "quantity": 1000.0,
        "supplier_capacity": 800.0,  # Small tier
    }
    report_small = validate_optimization_solution(sol_small, config)
    assert report_small.capacity_passed is False

    # Large tier supplier with 10,000 units capacity
    sol_large = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 10000.0,
        "quantity": 1000.0,
        "supplier_capacity": 10000.0,
    }
    report_large = validate_optimization_solution(sol_large, config)
    assert report_large.capacity_passed is True


# 7. Missing or invalid capacity is handled according to an explicit validation policy, not silently replaced with unlimited capacity
def test_invalid_or_negative_supplier_capacity_fails():
    config = get_baseline_scenario()

    # Case A: Negative capacity
    sol_neg = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 10000.0,
        "quantity": 100.0,
        "supplier_capacity": -50.0,
    }
    report_neg = validate_optimization_solution(sol_neg, config)
    assert report_neg.capacity_passed is False
    assert report_neg.is_valid is False

    # Case B: NaN capacity
    sol_nan = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 10000.0,
        "quantity": 100.0,
        "supplier_capacity": float("nan"),
    }
    report_nan = validate_optimization_solution(sol_nan, config)
    assert report_nan.capacity_passed is False
    assert report_nan.is_valid is False


# 8. A secondary supplier alternative is rejected if it exceeds that supplier's capacity
def test_secondary_supplier_exceeding_capacity_rejected(baseline_summary):
    config = get_baseline_scenario()

    opt_secondary_overcap = AlternativeOption(
        option_id="B",
        name="Secondary Supplier (Over Capacity)",
        feasibility=FeasibilityStatus.INFEASIBLE,
        estimated_total_cost=22000.0,
        objective_value=22000.0,
        constraint_violations=[
            ConstraintViolation(
                constraint_name="Supplier Capacity",
                limit_value=500.0,
                actual_value=800.0,
                violation_amount=300.0,
                message="Allocation exceeds secondary supplier capacity limit of 500 units",
            )
        ],
    )
    opt_air_compliant = AlternativeOption(
        option_id="A",
        name="Air Freight (Compliant)",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=28000.0,
        objective_value=28000.0,
    )

    ranked, winner_id, status, reason, _ = rank_alternatives(
        alternatives=[opt_secondary_overcap, opt_air_compliant],
        baseline=baseline_summary,
        config=config,
    )

    assert status == RecommendationStatus.FEASIBLE_RECOMMENDATION
    assert winner_id == "A"
    assert next(o for o in ranked if o.option_id == "B").is_recommended is False
    assert next(o for o in ranked if o.option_id == "A").is_recommended is True
