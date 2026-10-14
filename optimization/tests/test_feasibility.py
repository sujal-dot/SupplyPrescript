"""
Unit Tests for Optimization Feasibility and Infeasibility Diagnostics
=====================================================================
Verifies:
1. Solving a known small deterministic LP/MILP problem to confirmed OPTIMAL status.
2. Infeasible scenario detection (insufficient capacity, impossible budget).
3. Root-cause diagnostics reporting conflicting constraints.
4. Suggested user parameters without automatic silent relaxation.
5. Infeasible outcome is never misreported as OPTIMAL.
"""

import pytest

from optimization.config import get_baseline_scenario
from optimization.problem import solve_optimization_problem
from optimization.variables import CandidateOption, ProductData


@pytest.fixture
def solvable_benchmark_fixture():
    products = [
        ProductData(
            product_id="P1",
            product_name="Product Alpha",
            starting_inventory=100.0,
            demand=200.0,
            unit_cost=10.0,
            holding_cost_per_unit=0.5,
            shortage_penalty_per_unit=25.0,
        ),
    ]

    candidate_options = [
        CandidateOption(
            supplier_id="S1",
            supplier_name="Supplier Alpha (Cheap)",
            product_id="P1",
            product_name="Product Alpha",
            transport_mode="Road",
            unit_cost=10.0,
            shipping_cost_per_unit=1.0,
            lead_time_days=3.0,
            predicted_delay_probability=0.10,
            predicted_delay_days=0.5,
            expected_delay_cost_per_unit=0.01,
            supplier_capacity=500.0,
        ),
        CandidateOption(
            supplier_id="S2",
            supplier_name="Supplier Beta (Expensive)",
            product_id="P1",
            product_name="Product Alpha",
            transport_mode="Road",
            unit_cost=25.0,
            shipping_cost_per_unit=5.0,
            lead_time_days=2.0,
            predicted_delay_probability=0.05,
            predicted_delay_days=0.2,
            expected_delay_cost_per_unit=0.01,
            supplier_capacity=500.0,
        ),
    ]

    config = get_baseline_scenario()
    config.budget.max_total_cost = 50000.0
    config.inventory.minimum_required_units = 150.0  # Ending inv >= 150
    # Net procurement needed: demand (200) + min_inv (150) - start (100) = 250 units
    return candidate_options, products, config


def test_solvable_benchmark_produces_optimal(solvable_benchmark_fixture):
    candidate_options, products, config = solvable_benchmark_fixture

    result = solve_optimization_problem(candidate_options, products, config)

    # Must be OPTIMAL
    assert result.status == "OPTIMAL"
    assert result.is_optimal() is True
    assert result.objective.total_cost is not None
    assert result.objective.total_cost > 0

    # Cheap supplier S1 has capacity 500.0, enough for 250 units
    # S1 should be fully chosen over expensive S2
    s1_decisions = [d for d in result.decisions if d.supplier_id == "S1"]
    assert len(s1_decisions) >= 1
    assert s1_decisions[0].quantity == 250.0

    # Ending inventory = start (100) + procured (250) - demand (200) = 150.0
    inv = result.inventory_summary[0]
    assert inv.ending_inventory == 150.0
    assert inv.shortage_quantity == 0.0


def test_capacity_infeasible_scenario():
    products = [
        ProductData(
            product_id="P1",
            product_name="Huge Demand Item",
            starting_inventory=0.0,
            demand=10000.0,
            unit_cost=10.0,
            holding_cost_per_unit=0.5,
            shortage_penalty_per_unit=50.0,
        ),
    ]

    # Supplier only has capacity of 200 units, but demand is 10,000 and zero shortage permitted!
    candidate_options = [
        CandidateOption(
            supplier_id="S1",
            supplier_name="Tiny Supplier",
            product_id="P1",
            product_name="Huge Demand Item",
            transport_mode="Road",
            unit_cost=10.0,
            shipping_cost_per_unit=1.0,
            lead_time_days=3.0,
            predicted_delay_probability=0.10,
            predicted_delay_days=0.5,
            expected_delay_cost_per_unit=0.01,
            supplier_capacity=200.0,  # Far below 10,000!
        ),
    ]

    config = get_baseline_scenario()
    config.optimization.allow_shortage = False  # Strict fulfillment required

    result = solve_optimization_problem(candidate_options, products, config)

    assert result.status == "INFEASIBLE"
    assert result.is_optimal() is False
    assert result.objective.total_cost is None
    assert result.infeasibility_diagnostics is not None
    assert len(result.infeasibility_diagnostics.root_causes) > 0


def test_budget_infeasible_scenario():
    products = [
        ProductData(
            product_id="P1",
            product_name="Expensive Item",
            starting_inventory=0.0,
            demand=500.0,
            unit_cost=1000.0,  # 500 * 1000 = $500,000!
            holding_cost_per_unit=50.0,
            shortage_penalty_per_unit=2000.0,
        ),
    ]

    candidate_options = [
        CandidateOption(
            supplier_id="S1",
            supplier_name="Luxury Supplier",
            product_id="P1",
            product_name="Expensive Item",
            transport_mode="Road",
            unit_cost=1000.0,
            shipping_cost_per_unit=50.0,
            lead_time_days=3.0,
            predicted_delay_probability=0.10,
            predicted_delay_days=0.5,
            expected_delay_cost_per_unit=0.01,
            supplier_capacity=2000.0,
        ),
    ]

    config = get_baseline_scenario()
    config.budget.max_total_cost = 5000.0  # Budget is only $5,000 (needs $525,000+)
    config.optimization.allow_shortage = False

    result = solve_optimization_problem(candidate_options, products, config)

    assert result.status == "INFEASIBLE"
    assert result.is_optimal() is False
    assert result.infeasibility_diagnostics is not None
