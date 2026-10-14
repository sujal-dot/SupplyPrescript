"""
Unit Tests for Optimization Decision Variables
==============================================
Verifies:
1. Decision variables creation for candidate procurement and shipping options.
2. Non-negativity lower bounds (lowBound >= 0).
3. Integer vs Continuous category selection.
4. Upper bounding by supplier capacity.
5. Linear expression aggregation by product, supplier, and transport mode.
"""

import pulp
import pytest

from optimization.config import get_baseline_scenario, ScenarioConfig
from optimization.variables import (
    CandidateOption,
    OptimizationVariables,
    ProductData,
    create_decision_variables,
)


@pytest.fixture
def sample_fixture():
    products = [
        ProductData(
            product_id="PROD001",
            product_name="Microcontroller IC",
            starting_inventory=200.0,
            demand=500.0,
            unit_cost=50.0,
            holding_cost_per_unit=2.5,
            shortage_penalty_per_unit=75.0,
            minimum_inventory=100.0,
        ),
        ProductData(
            product_id="PROD002",
            product_name="Power Supply 24V",
            starting_inventory=150.0,
            demand=300.0,
            unit_cost=120.0,
            holding_cost_per_unit=6.0,
            shortage_penalty_per_unit=180.0,
            minimum_inventory=50.0,
        ),
    ]

    candidate_options = [
        CandidateOption(
            supplier_id="SUP001",
            supplier_name="Apex Electronics",
            product_id="PROD001",
            product_name="Microcontroller IC",
            transport_mode="Road",
            unit_cost=50.0,
            shipping_cost_per_unit=4.0,
            lead_time_days=4.0,
            predicted_delay_probability=0.12,
            predicted_delay_days=0.5,
            expected_delay_cost_per_unit=0.015,
            supplier_capacity=2000.0,
        ),
        CandidateOption(
            supplier_id="SUP001",
            supplier_name="Apex Electronics",
            product_id="PROD001",
            product_name="Microcontroller IC",
            transport_mode="Air",
            unit_cost=50.0,
            shipping_cost_per_unit=12.0,
            lead_time_days=1.5,
            predicted_delay_probability=0.04,
            predicted_delay_days=0.1,
            expected_delay_cost_per_unit=0.005,
            supplier_capacity=2000.0,
        ),
        CandidateOption(
            supplier_id="SUP002",
            supplier_name="Havells Components",
            product_id="PROD002",
            product_name="Power Supply 24V",
            transport_mode="Road",
            unit_cost=120.0,
            shipping_cost_per_unit=8.0,
            lead_time_days=3.0,
            predicted_delay_probability=0.20,
            predicted_delay_days=1.2,
            expected_delay_cost_per_unit=0.060,
            supplier_capacity=1500.0,
        ),
    ]

    config = get_baseline_scenario()
    return candidate_options, products, config


def test_decision_variables_creation(sample_fixture):
    candidate_options, products, config = sample_fixture
    problem = pulp.LpProblem("TestVars", pulp.LpMinimize)

    variables = create_decision_variables(problem, candidate_options, products, config)

    # 3 options -> 3 q variables
    assert len(variables.q) == 3
    # 2 products -> 2 ending inventory variables and 2 shortage variables
    assert len(variables.I) == 2
    assert len(variables.u) == 2

    # Verify keys
    assert ("SUP001", "PROD001", "Road") in variables.q
    assert ("SUP001", "PROD001", "Air") in variables.q
    assert ("SUP002", "PROD002", "Road") in variables.q
    assert "PROD001" in variables.I
    assert "PROD002" in variables.I


def test_decision_variables_non_negativity(sample_fixture):
    candidate_options, products, config = sample_fixture
    problem = pulp.LpProblem("TestVarsNonNeg", pulp.LpMinimize)

    variables = create_decision_variables(problem, candidate_options, products, config)

    # All q variables must have lowBound == 0
    for key, var in variables.q.items():
        assert var.lowBound == 0, f"Variable {key} lowBound is not 0"

    # All I and u variables must have lowBound == 0
    for p_id, var in variables.I.items():
        assert var.lowBound == 0
    for p_id, var in variables.u.items():
        assert var.lowBound == 0


def test_decision_variables_capacity_upper_bound(sample_fixture):
    candidate_options, products, config = sample_fixture
    problem = pulp.LpProblem("TestVarsUpBound", pulp.LpMinimize)

    variables = create_decision_variables(problem, candidate_options, products, config)

    # SUP001 has capacity 2000.0
    var_road = variables.q[("SUP001", "PROD001", "Road")]
    assert var_road.upBound == 2000.0

    # SUP002 has capacity 1500.0
    var_havells = variables.q[("SUP002", "PROD002", "Road")]
    assert var_havells.upBound == 1500.0


def test_decision_variables_category_integer_vs_continuous(sample_fixture):
    candidate_options, products, config = sample_fixture

    # Test integer
    prob_int = pulp.LpProblem("TestInt", pulp.LpMinimize)
    config.optimization.integer_quantities = True
    vars_int = create_decision_variables(prob_int, candidate_options, products, config)
    for var in vars_int.q.values():
        assert var.cat in ("Integer", pulp.const.LpInteger if hasattr(pulp.const, "LpInteger") else "Integer")

    # Test continuous
    prob_cont = pulp.LpProblem("TestCont", pulp.LpMinimize)
    config.optimization.integer_quantities = False
    vars_cont = create_decision_variables(prob_cont, candidate_options, products, config)
    for var in vars_cont.q.values():
        assert var.cat in ("Continuous", pulp.const.LpContinuous if hasattr(pulp.const, "LpContinuous") else "Continuous")


def test_decision_variables_aggregation_helpers(sample_fixture):
    candidate_options, products, config = sample_fixture
    problem = pulp.LpProblem("TestAgg", pulp.LpMinimize)
    variables = create_decision_variables(problem, candidate_options, products, config)

    # Aggregation for PROD001 should include Road and Air
    expr_p1 = variables.get_procured_for_product("PROD001")
    assert isinstance(expr_p1, pulp.LpAffineExpression)

    # Aggregation for SUP001 should include both PROD001 options
    expr_s1 = variables.get_procured_from_supplier("SUP001")
    assert isinstance(expr_s1, pulp.LpAffineExpression)

    # Mode aggregation
    expr_road = variables.get_procured_by_mode("Road")
    assert isinstance(expr_road, pulp.LpAffineExpression)
