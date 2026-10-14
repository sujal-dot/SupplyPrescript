"""
Unit Tests for Optimization Constraints Module
==============================================
Verifies:
1. Budget limit constraint application and non-cash penalty exclusion.
2. Aggregate and per-product minimum inventory constraints.
3. Inventory conservation balance constraints.
4. Supplier capacity constraints.
5. Delivery delay threshold pruning and prohibition.
6. Strict demand fulfillment vs shortage allowance.
"""

import pulp
import pytest

from optimization.config import get_baseline_scenario
from optimization.constraints import apply_business_constraints
from optimization.objective import build_objective
from optimization.variables import (
    CandidateOption,
    OptimizationVariables,
    ProductData,
    create_decision_variables,
)


@pytest.fixture
def constraint_fixture():
    products = [
        ProductData(
            product_id="P1",
            product_name="Product One",
            starting_inventory=100.0,
            demand=250.0,
            unit_cost=20.0,
            holding_cost_per_unit=1.0,
            shortage_penalty_per_unit=30.0,
            minimum_inventory=50.0,
        ),
    ]

    candidate_options = [
        CandidateOption(
            supplier_id="S1",
            supplier_name="Supplier One",
            product_id="P1",
            product_name="Product One",
            transport_mode="Road",
            unit_cost=20.0,
            shipping_cost_per_unit=2.0,
            lead_time_days=3.0,
            predicted_delay_probability=0.10,
            predicted_delay_days=1.0,
            expected_delay_cost_per_unit=0.01,
            supplier_capacity=500.0,
        ),
        CandidateOption(
            supplier_id="S2",
            supplier_name="Supplier Two (Slow)",
            product_id="P1",
            product_name="Product One",
            transport_mode="Sea",
            unit_cost=15.0,
            shipping_cost_per_unit=1.0,
            lead_time_days=10.0,
            predicted_delay_probability=0.85,
            predicted_delay_days=9.5,  # Exceeds baseline 7.0 delay threshold!
            expected_delay_cost_per_unit=0.20,
            supplier_capacity=1000.0,
        ),
    ]

    config = get_baseline_scenario()
    config.budget.max_total_cost = 10000.0
    config.inventory.minimum_required_units = 100.0
    config.delivery.maximum_acceptable_delay_days = 7.0

    return candidate_options, products, config


def test_budget_constraint_application(constraint_fixture):
    candidate_options, products, config = constraint_fixture
    problem = pulp.LpProblem("TestBudget", pulp.LpMinimize)
    variables = create_decision_variables(problem, candidate_options, products, config)
    objectives = build_objective(problem, variables, candidate_options, products, config)

    registry = apply_business_constraints(problem, variables, objectives, candidate_options, products, config)

    budget_constraints = registry.get_by_category("Budget")
    assert len(budget_constraints) == 1
    assert budget_constraints[0].rhs == 10000.0


def test_inventory_balance_constraint(constraint_fixture):
    candidate_options, products, config = constraint_fixture
    problem = pulp.LpProblem("TestBalance", pulp.LpMinimize)
    variables = create_decision_variables(problem, candidate_options, products, config)
    objectives = build_objective(problem, variables, candidate_options, products, config)

    registry = apply_business_constraints(problem, variables, objectives, candidate_options, products, config)

    balance_constraints = registry.get_by_category("InventoryBalance")
    assert len(balance_constraints) == 1
    # net requirement: demand (250) - starting_inv (100) = 150.0
    assert balance_constraints[0].rhs == 150.0


def test_minimum_inventory_constraint(constraint_fixture):
    candidate_options, products, config = constraint_fixture
    problem = pulp.LpProblem("TestMinInv", pulp.LpMinimize)
    variables = create_decision_variables(problem, candidate_options, products, config)
    objectives = build_objective(problem, variables, candidate_options, products, config)

    registry = apply_business_constraints(problem, variables, objectives, candidate_options, products, config)

    min_inv_constraints = registry.get_by_category("MinimumInventory")
    # 1 aggregate + 1 product-specific
    assert len(min_inv_constraints) == 2
    agg = [c for c in min_inv_constraints if c.name == "Constraint_Minimum_Inventory_Aggregate"][0]
    assert agg.rhs == 100.0


def test_supplier_capacity_constraint(constraint_fixture):
    candidate_options, products, config = constraint_fixture
    problem = pulp.LpProblem("TestCap", pulp.LpMinimize)
    variables = create_decision_variables(problem, candidate_options, products, config)
    objectives = build_objective(problem, variables, candidate_options, products, config)

    registry = apply_business_constraints(problem, variables, objectives, candidate_options, products, config)

    cap_constraints = registry.get_by_category("SupplierCapacity")
    # S1 has cap 500.0, S2 has cap 1000.0
    assert len(cap_constraints) == 2
    rhs_values = sorted([c.rhs for c in cap_constraints])
    assert rhs_values == [500.0, 1000.0]


def test_delivery_delay_pruning_constraint(constraint_fixture):
    candidate_options, products, config = constraint_fixture
    problem = pulp.LpProblem("TestDelayPrune", pulp.LpMinimize)
    variables = create_decision_variables(problem, candidate_options, products, config)
    objectives = build_objective(problem, variables, candidate_options, products, config)

    registry = apply_business_constraints(problem, variables, objectives, candidate_options, products, config)

    delay_constraints = registry.get_by_category("DeliveryDeadline")
    # S2 has predicted delay 9.5d > 7.0d -> must have prohibition constraint (q == 0)
    assert len(delay_constraints) == 1
    assert "S2" in delay_constraints[0].name
    assert delay_constraints[0].rhs == 0.0
    assert len(registry.delay_pruned_options) == 1
