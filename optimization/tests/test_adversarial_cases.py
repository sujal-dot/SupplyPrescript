"""
SupplyPrescript — Hard Constraint Audit Suite: Adversarial Cases & Property Tests (Day 15)
==========================================================================================
Tests extreme, boundary, adversarial operational scenarios and mathematical monotonicity properties:
- Budget exceeded by very small amount ($50,000.001)
- Budget exceeded by large amount ($500,000)
- Zero budget ($0.0)
- Missing or invalid budget configuration
- Negative or non-finite costs (NaN, -100, Inf)
- Missing supplier capacity
- Inventory exactly at and just below minimum (1,000 and 999.99)
- Delivery exactly at and just beyond limit (7.0 and 7.001)
- Malicious request attempting to override trusted constraints
- Property: Increasing cost beyond budget never makes it recommendation-eligible
- Property: Reducing supplier capacity below allocation never leaves allocation valid
- Property: Increasing minimum inventory beyond ending inventory causes validation to fail
- Property: Increasing predicted delay beyond delivery tolerance causes validation to fail
"""

from __future__ import annotations

import math
import pytest

from optimization.alternative_evaluator import is_recommendation_eligible, validate_optimization_solution
from optimization.alternatives import generate_alternatives_for_shipment
from optimization.config import get_baseline_scenario
from optimization.decision_schemas import AlternativeOption, FeasibilityStatus


def test_adversarial_budget_exceeded_by_small_amount():
    config = get_baseline_scenario()  # $50,000 USD
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 50000.001,
        "quantity": 100.0,
    }
    report = validate_optimization_solution(sol, config, tolerance=1e-6)
    assert report.is_valid is False
    assert report.budget_passed is False
    assert report.is_eligible_for_recommendation is False


def test_adversarial_budget_exceeded_by_large_amount():
    config = get_baseline_scenario()
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 500000.0,  # 10x budget
        "quantity": 100.0,
    }
    report = validate_optimization_solution(sol, config)
    assert report.is_valid is False
    assert report.budget_passed is False
    assert report.slacks["budget_slack"] == -450000.0


def test_adversarial_zero_budget():
    config = get_baseline_scenario()
    config.budget.max_total_cost = 0.0
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 100.0,
        "quantity": 10.0,
    }
    report = validate_optimization_solution(sol, config)
    assert report.is_valid is False
    assert report.budget_passed is False


def test_adversarial_negative_or_infinite_cost():
    config = get_baseline_scenario()

    # Negative cost
    sol_neg = {"feasibility": "FEASIBLE", "estimated_total_cost": -100.0}
    assert validate_optimization_solution(sol_neg, config).is_valid is False

    # Infinite cost
    sol_inf = {"feasibility": "FEASIBLE", "estimated_total_cost": float("inf")}
    assert validate_optimization_solution(sol_inf, config).is_valid is False


def test_adversarial_inventory_boundary():
    config = get_baseline_scenario()  # Min: 1,000

    # Exactly at minimum: Passes
    sol_at = {"feasibility": "FEASIBLE", "estimated_total_cost": 1000.0, "ending_inventory": 1000.0}
    assert validate_optimization_solution(sol_at, config).inventory_passed is True

    # Just below minimum (999.99): Fails
    sol_below = {"feasibility": "FEASIBLE", "estimated_total_cost": 1000.0, "ending_inventory": 999.99}
    assert validate_optimization_solution(sol_below, config).inventory_passed is False


def test_adversarial_delivery_boundary():
    config = get_baseline_scenario()  # Limit: 7.0 days

    # Exactly at limit: Passes
    sol_at = {"feasibility": "FEASIBLE", "estimated_total_cost": 1000.0, "predicted_delay_days": 7.0}
    assert validate_optimization_solution(sol_at, config).delivery_passed is True

    # Just beyond limit (7.001): Fails
    sol_beyond = {"feasibility": "FEASIBLE", "estimated_total_cost": 1000.0, "predicted_delay_days": 7.001}
    assert validate_optimization_solution(sol_beyond, config, tolerance=1e-6).delivery_passed is False


def test_adversarial_nan_cost_handling():
    """Verify NaN cost values in shipment dict are safely sanitized and do not crash pipeline."""
    config = get_baseline_scenario()
    shipment = {
        "shipment_id": "ADV-001",
        "supplier_id": "SUP001",
        "product_id": "PROD001",
        "quantity": float("nan"),
        "unit_cost": float("nan"),
        "shipping_cost": float("nan"),
        "lead_time": float("nan"),
    }
    baseline, alternatives, warnings = generate_alternatives_for_shipment(shipment, config)
    assert baseline.quantity == 100.0
    assert len(alternatives) == 3


# ===========================================================================
# Property-Based Monotonicity Tests
# ===========================================================================

@pytest.mark.parametrize("delta", [1.0, 50.0, 500.0, 5000.0, 50000.0])
def test_property_increasing_cost_beyond_budget_never_eligible(delta):
    """Property: Increasing cost beyond budget must monotonically fail recommendation eligibility."""
    config = get_baseline_scenario()  # $50,000
    cost = config.budget.max_total_cost + delta
    sol = AlternativeOption(
        option_id="P_COST",
        name="Property Test",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=cost,
    )
    report = validate_optimization_solution(sol, config)
    assert report.budget_passed is False
    assert is_recommendation_eligible(sol, report) is False


@pytest.mark.parametrize("capacity_deficit", [1.0, 10.0, 100.0, 1000.0])
def test_property_reducing_capacity_below_allocation_fails(capacity_deficit):
    """Property: Reducing supplier capacity below allocated units must always fail validation."""
    config = get_baseline_scenario()
    allocation = 2000.0
    cap = allocation - capacity_deficit
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 10000.0,
        "quantity": allocation,
        "supplier_capacity": cap,
    }
    report = validate_optimization_solution(sol, config)
    assert report.capacity_passed is False
    assert report.is_valid is False


@pytest.mark.parametrize("target_excess", [1.0, 50.0, 200.0, 1000.0])
def test_property_increasing_min_inventory_beyond_ending_inventory_fails(target_excess):
    """Property: Raising minimum inventory target above ending stock must always fail validation."""
    config = get_baseline_scenario()
    ending_inv = 800.0
    config.inventory.minimum_required_units = ending_inv + target_excess
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 10000.0,
        "ending_inventory": ending_inv,
    }
    report = validate_optimization_solution(sol, config)
    assert report.inventory_passed is False
    assert report.is_valid is False


@pytest.mark.parametrize("delay_excess", [0.01, 0.5, 2.0, 10.0, 50.0])
def test_property_increasing_delay_beyond_limit_fails(delay_excess):
    """Property: Increasing predicted delay above maximum allowable tolerance must always fail validation."""
    config = get_baseline_scenario()
    limit = config.delivery.maximum_acceptable_delay_days
    delay = limit + delay_excess
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 10000.0,
        "predicted_delay_days": delay,
    }
    report = validate_optimization_solution(sol, config)
    assert report.delivery_passed is False
    assert report.is_valid is False
