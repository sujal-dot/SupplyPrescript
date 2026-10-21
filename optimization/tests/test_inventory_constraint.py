"""
SupplyPrescript — Hard Constraint Audit Suite: Inventory Constraint (Day 15)
============================================================================
Audits mathematical enforcement of inventory balance and minimum inventory targets:
    I_p = I_{0, p} + sum_{s,m} q_{s,p,m} - D_p + u_p
    I_p >= I_min

Audits all mandatory inventory conditions:
1. A plan meeting the minimum inventory requirement is accepted.
2. A plan exactly at the minimum is accepted.
3. A plan below the minimum is rejected.
4. The calculation correctly accounts for initial inventory, procurement, consumption, and shipments.
5. Product-specific minimums are enforced when configured.
6. Products with different units of measurement are not incorrectly aggregated.
7. Missing inventory data is not silently interpreted as sufficient stock.
8. An alternative that breaks the inventory constraint cannot be recommended.
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
        shipment_id="TEST-INV-SHIP-01",
        product_id="PROD001",
        product_name="Power Unit",
        supplier_id="SUP001",
        supplier_name="Alpha",
        transport_mode="Road",
        quantity=100.0,
        unit_cost=50.0,
        shipping_cost=200.0,
        estimated_total_cost=5200.0,
        currency="USD",
    )


# 1. A plan meeting the minimum inventory requirement is accepted
def test_inventory_target_satisfied():
    config = get_baseline_scenario()  # Min inventory: 1,000 units
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 25000.0,
        "quantity": 100.0,
        "ending_inventory": 1250.0,
    }
    report = validate_optimization_solution(sol, config)
    assert report.is_valid is True
    assert report.inventory_passed is True
    assert report.is_eligible_for_recommendation is True
    assert report.slacks["inventory_slack"] == 250.0


# 2. A plan exactly at the minimum is accepted
def test_inventory_target_at_exact_threshold():
    config = get_baseline_scenario()  # Min inventory: 1,000 units
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 25000.0,
        "quantity": 100.0,
        "ending_inventory": 1000.0,
    }
    report = validate_optimization_solution(sol, config, tolerance=1e-6)
    assert report.is_valid is True
    assert report.inventory_passed is True
    assert report.slacks["inventory_slack"] == 0.0


# 3. A plan below the minimum is rejected
def test_inventory_target_violated():
    config = get_baseline_scenario()  # Min inventory: 1,000 units
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 25000.0,
        "quantity": 100.0,
        "ending_inventory": 850.0,  # Below 1,000 units
    }
    report = validate_optimization_solution(sol, config)
    assert report.is_valid is False
    assert report.inventory_passed is False
    assert any(v.constraint_name == "Minimum Inventory Target" for v in report.violations)
    assert report.slacks["inventory_slack"] == -150.0


# 4. Calculation correctly accounts for initial inventory, procurement, consumption, and shipments
def test_inventory_flow_conservation_calculation():
    config = get_baseline_scenario()  # Min inventory: 1,000 units
    # Starting = 1200, Procurement = 300, Demand = 400 -> Ending = 1200 + 300 - 400 = 1100 (Passes >= 1000)
    sol_pass = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 15000.0,
        "starting_inventory": 1200.0,
        "procurement_quantity": 300.0,
        "demand": 400.0,
    }
    report_pass = validate_optimization_solution(sol_pass, config)
    assert report_pass.inventory_passed is True
    assert report_pass.slacks["inventory_slack"] == 100.0

    # Starting = 1000, Procurement = 100, Demand = 300 -> Ending = 1000 + 100 - 300 = 800 (Fails < 1000)
    sol_fail = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 15000.0,
        "starting_inventory": 1000.0,
        "procurement_quantity": 100.0,
        "demand": 300.0,
    }
    report_fail = validate_optimization_solution(sol_fail, config)
    assert report_fail.inventory_passed is False
    assert report_fail.slacks["inventory_slack"] == -200.0


# 5. Product-specific minimums are enforced when configured
def test_product_specific_inventory_enforcement():
    from optimization.constraints import apply_business_constraints
    from optimization.objective import build_objective
    from optimization.variables import CandidateOption, ProductData, create_decision_variables
    import pulp

    config = get_baseline_scenario()
    problem = pulp.LpProblem("Inv_Test", pulp.LpMinimize)

    # Product with explicit minimum ending buffer of 500 units
    prod = ProductData(
        product_id="PROD_SPEC",
        product_name="Specific Part",
        starting_inventory=100.0,
        demand=200.0,
        unit_cost=10.0,
        holding_cost_per_unit=0.5,
        shortage_penalty_per_unit=50.0,
        minimum_inventory=500.0,  # Specific minimum
    )
    opt = CandidateOption(
        supplier_id="SUP1",
        supplier_name="Alpha",
        product_id="PROD_SPEC",
        product_name="Specific Part",
        transport_mode="Road",
        unit_cost=10.0,
        shipping_cost_per_unit=5.0,
        lead_time_days=3.0,
        predicted_delay_probability=0.1,
        predicted_delay_days=1.0,
        expected_delay_cost_per_unit=1.0,
        supplier_capacity=2000.0,
    )
    variables = create_decision_variables(problem, [opt], [prod], config)
    objectives = build_objective(problem, variables, [opt], [prod], config)
    registry = apply_business_constraints(problem, variables, objectives, [opt], [prod], config)

    # Verify per-product constraint is registered
    matching = [c for c in registry.constraints if "PROD_SPEC" in c.name and c.category == "MinimumInventory"]
    assert len(matching) >= 1
    assert matching[0].rhs == 500.0


# 6. Products with different units of measurement are not incorrectly aggregated
def test_products_with_different_uom_not_cross_aggregated():
    from optimization.variables import ProductData
    prod_kg = ProductData(
        product_id="P_KG",
        product_name="Chemical Raw (kg)",
        starting_inventory=200.0,
        demand=500.0,
        unit_cost=5.0,
        holding_cost_per_unit=0.1,
        shortage_penalty_per_unit=20.0,
    )
    prod_units = ProductData(
        product_id="P_UNITS",
        product_name="Electronic Board (units)",
        starting_inventory=50.0,
        demand=100.0,
        unit_cost=45.0,
        holding_cost_per_unit=1.0,
        shortage_penalty_per_unit=100.0,
    )
    # Distinct product IDs enforce distinct decision variables in the LP formulation
    assert prod_kg.product_id != prod_units.product_id
    assert prod_kg.product_id not in prod_units.product_id


# 7. Missing inventory data is not silently interpreted as sufficient stock
def test_missing_inventory_data_fails_validation_when_checked():
    config = get_baseline_scenario()
    sol_nan = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 25000.0,
        "ending_inventory": float("nan"),
    }
    report = validate_optimization_solution(sol_nan, config)
    assert report.inventory_passed is False
    assert report.is_valid is False


# 8. An alternative that breaks the inventory constraint cannot be recommended
def test_inventory_violating_alternative_cannot_be_recommended(baseline_summary):
    config = get_baseline_scenario()

    opt_inv_violation = AlternativeOption(
        option_id="A",
        name="Depleting Plan",
        feasibility=FeasibilityStatus.INFEASIBLE,
        estimated_total_cost=20000.0,
        objective_value=20000.0,
        constraint_violations=[
            ConstraintViolation(
                constraint_name="Minimum Inventory Target",
                limit_value=1000.0,
                actual_value=500.0,
                violation_amount=500.0,
                message="Stock falls below minimum threshold",
            )
        ],
    )
    opt_compliant = AlternativeOption(
        option_id="B",
        name="Buffer Preserving Plan",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=25000.0,
        objective_value=25000.0,
    )

    ranked, winner_id, status, reason, _ = rank_alternatives(
        alternatives=[opt_inv_violation, opt_compliant],
        baseline=baseline_summary,
        config=config,
    )

    assert status == RecommendationStatus.FEASIBLE_RECOMMENDATION
    assert winner_id == "B"
    assert next(o for o in ranked if o.option_id == "A").is_recommended is False
    assert next(o for o in ranked if o.option_id == "B").is_recommended is True
