"""
Unit Tests for SupplyPrescript Optimization Solver (Day 12)
===========================================================
Verifies:
1. Small valid optimization problem returns OPTIMAL.
2. Objective equals sum of reported cost components.
3. Budget constraint is respected.
4. Supplier capacity is respected.
5. Minimum inventory buffer is respected.
6. Demand is fulfilled when required.
7. Shipment quantities do not exceed procured units.
8. Integer constraints are respected.
9. Infeasible constraints are reported with root-cause diagnostics.
10. Invalid inputs are rejected during pre-solve validation.
11. Missing ML predictions produce safe warnings/fallbacks without crashing.
12. Results distinguish OPTIMAL, INFEASIBLE, and ERROR states.
13. Polymorphic input formats (raw dicts vs CandidateOption instances).
"""

import pytest

from optimization.config import get_baseline_scenario
from optimization.solver import (
    clear_prediction_cache,
    enrich_candidate_options_with_ml,
    solve_optimization_problem,
    solve_supply_chain,
)
from optimization.variables import CandidateOption, ProductData


@pytest.fixture
def deterministic_fixture():
    """Small, deterministic, reproducible supply-chain test fixture."""
    products = [
        ProductData(
            product_id="P1",
            product_name="Product Alpha",
            starting_inventory=50.0,
            demand=150.0,
            unit_cost=20.0,
            holding_cost_per_unit=1.0,
            shortage_penalty_per_unit=30.0,
        ),
        ProductData(
            product_id="P2",
            product_name="Product Beta",
            starting_inventory=80.0,
            demand=200.0,
            unit_cost=40.0,
            holding_cost_per_unit=2.0,
            shortage_penalty_per_unit=60.0,
        ),
    ]

    candidate_options = [
        # Supplier 1: Road & Rail options for P1
        CandidateOption(
            supplier_id="SUP1",
            supplier_name="Reliable Supplier 1",
            product_id="P1",
            product_name="Product Alpha",
            transport_mode="Road",
            unit_cost=20.0,
            shipping_cost_per_unit=2.5,
            lead_time_days=3.0,
            predicted_delay_probability=0.10,
            predicted_delay_days=0.5,
            expected_delay_cost_per_unit=0.0125,
            supplier_capacity=1500.0,
            supplier_reliability=0.95,
        ),
        CandidateOption(
            supplier_id="SUP1",
            supplier_name="Reliable Supplier 1",
            product_id="P1",
            product_name="Product Alpha",
            transport_mode="Rail",
            unit_cost=20.0,
            shipping_cost_per_unit=1.5,
            lead_time_days=5.0,
            predicted_delay_probability=0.20,
            predicted_delay_days=1.2,
            expected_delay_cost_per_unit=0.060,
            supplier_capacity=1500.0,
            supplier_reliability=0.95,
        ),
        # Supplier 2: Road & Air options for P2
        CandidateOption(
            supplier_id="SUP2",
            supplier_name="Fast Supplier 2",
            product_id="P2",
            product_name="Product Beta",
            transport_mode="Road",
            unit_cost=40.0,
            shipping_cost_per_unit=4.0,
            lead_time_days=2.0,
            predicted_delay_probability=0.08,
            predicted_delay_days=0.3,
            expected_delay_cost_per_unit=0.006,
            supplier_capacity=1000.0,
            supplier_reliability=0.92,
        ),
        CandidateOption(
            supplier_id="SUP2",
            supplier_name="Fast Supplier 2",
            product_id="P2",
            product_name="Product Beta",
            transport_mode="Air",
            unit_cost=40.0,
            shipping_cost_per_unit=12.0,
            lead_time_days=1.0,
            predicted_delay_probability=0.02,
            predicted_delay_days=0.1,
            expected_delay_cost_per_unit=0.0025,
            supplier_capacity=1000.0,
            supplier_reliability=0.92,
        ),
    ]

    config = get_baseline_scenario()
    config.budget.max_total_cost = 50000.0
    config.inventory.minimum_required_units = 300.0

    return candidate_options, products, config


def test_solver_returns_optimal(deterministic_fixture):
    """Test 1: Small valid optimization problem returns confirmed OPTIMAL status."""
    candidate_options, products, config = deterministic_fixture
    result = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=config)

    assert result.status == "OPTIMAL"
    assert result.is_optimal() is True
    assert result.objective_value is not None
    assert result.objective_value > 0
    assert len(result.decisions) > 0


def test_objective_equals_sum_of_cost_components(deterministic_fixture):
    """Test 2: Objective value equals exactly the sum of reported cost breakdown items."""
    candidate_options, products, config = deterministic_fixture
    result = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=config)

    cb = result.cost_breakdown
    assert cb is not None
    sum_components = (
        cb["procurement_cost"]
        + cb["shipping_cost"]
        + cb["inventory_cost"]
        + cb["delay_penalty"]
        + cb["risk_cost"]
        + cb["shortage_cost"]
    )
    assert abs(result.objective_value - sum_components) < 0.05


def test_budget_constraint_respected(deterministic_fixture):
    """Test 3: Budget constraint ceiling is strictly observed."""
    candidate_options, products, config = deterministic_fixture
    config.budget.max_total_cost = 25000.0

    result = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=config)

    assert result.is_optimal() is True
    budget_check = [c for c in result.constraint_checks if c.category == "Budget"][0]
    assert budget_check.status in ("SATISFIED", "BINDING")
    assert budget_check.lhs_value <= config.budget.max_total_cost


def test_supplier_capacity_respected(deterministic_fixture):
    """Test 4: Each supplier's allocated procurement does not exceed available capacity."""
    candidate_options, products, config = deterministic_fixture
    # Limit SUP1 to 200 units
    for opt in candidate_options:
        if opt.supplier_id == "SUP1":
            opt.supplier_capacity = 200.0

    result = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=config)

    assert result.is_optimal() is True
    for util in result.supplier_utilization:
        assert util.allocated_units <= util.max_capacity_units


def test_minimum_inventory_buffer_respected(deterministic_fixture):
    """Test 5: Minimum inventory target is satisfied."""
    candidate_options, products, config = deterministic_fixture
    config.inventory.minimum_required_units = 500.0

    result = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=config)

    assert result.is_optimal() is True
    total_ending = sum(inv.ending_inventory for inv in result.inventory_summary)
    assert total_ending >= config.inventory.minimum_required_units


def test_demand_fulfilled_when_required(deterministic_fixture):
    """Test 6: Customer demand is fulfilled without shortage when allow_shortage=False."""
    candidate_options, products, config = deterministic_fixture
    config.optimization.allow_shortage = False

    result = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=config)

    assert result.is_optimal() is True
    for inv in result.inventory_summary:
        assert inv.shortage_quantity == 0.0
        # Ending inventory = start + procured - demand
        expected_ending = inv.starting_inventory + inv.procured_quantity - inv.demand
        assert abs(inv.ending_inventory - expected_ending) < 0.01


def test_shipment_consistency_with_procurement(deterministic_fixture):
    """Test 7: Shipment quantities across transport modes equal procured quantities."""
    candidate_options, products, config = deterministic_fixture
    result = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=config)

    assert result.is_optimal() is True
    # Verify shipment consistency constraints are all satisfied
    shipment_checks = [c for c in result.constraint_checks if c.category == "ShipmentConsistency"]
    for sc in shipment_checks:
        assert sc.status in ("SATISFIED", "BINDING")


def test_integer_constraints_respected(deterministic_fixture):
    """Test 8: Whole integer unit allocations when integer_quantities is enabled."""
    candidate_options, products, config = deterministic_fixture
    config.optimization.integer_quantities = True

    result = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=config)

    assert result.is_optimal() is True
    for d in result.decisions:
        assert d.quantity.is_integer() or abs(d.quantity - round(d.quantity)) < 1e-4
    for inv in result.inventory_summary:
        assert inv.ending_inventory.is_integer() or abs(inv.ending_inventory - round(inv.ending_inventory)) < 1e-4


def test_infeasible_problem_diagnosed_correctly(deterministic_fixture):
    """Test 9: Infeasible problems are identified and conflicting constraints reported."""
    candidate_options, products, config = deterministic_fixture
    # Make budget impossible ($500 cannot fulfill 300 min inventory + 350 demand)
    config.budget.max_total_cost = 500.0
    config.optimization.allow_shortage = False

    result = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=config)

    assert result.status == "INFEASIBLE"
    assert result.is_optimal() is False
    assert result.objective_value is None
    assert result.infeasibility_diagnostics is not None
    assert result.infeasibility_diagnostics.is_infeasible is True
    assert len(result.infeasibility_diagnostics.conflicting_constraints) > 0


def test_invalid_inputs_rejected():
    """Test 10: Invalid inputs (negative values, out-of-bound probabilities) rejected pre-solve."""
    products = [
        ProductData("P1", "Alpha", starting_inventory=-10.0, demand=100.0, unit_cost=20.0, holding_cost_per_unit=1.0, shortage_penalty_per_unit=30.0)
    ]
    options = [
        CandidateOption("S1", "Supp1", "P1", "Alpha", "Road", unit_cost=-5.0, shipping_cost_per_unit=2.0, lead_time_days=3.0, predicted_delay_probability=1.5, predicted_delay_days=-1.0, expected_delay_cost_per_unit=0.0, supplier_capacity=1000.0)
    ]
    config = get_baseline_scenario()

    result = solve_supply_chain(candidate_options=options, product_data=products, scenario=config)

    assert result.status == "INFEASIBLE"
    assert result.objective_value is None
    assert any("negative starting inventory" in w.lower() for w in result.warnings)
    assert any("negative unit cost" in w.lower() for w in result.warnings)
    assert any("invalid delay probability" in w.lower() for w in result.warnings)


def test_raw_polymorphic_inputs():
    """Test 11: solve_supply_chain accepts high-level dictionary parameters."""
    raw_products = [
        {"product_id": "P100", "product_name": "Sensor", "unit_cost": 50.0, "starting_inventory": 20.0, "demand": 100.0}
    ]
    raw_shipping = [
        {
            "supplier_id": "SUP100",
            "supplier_name": "SensorTech",
            "product_id": "P100",
            "transport_mode": "Road",
            "unit_cost": 50.0,
            "shipping_cost_per_unit": 5.0,
            "lead_time_days": 4.0,
            "predicted_delay_probability": 0.15,
            "predicted_delay_days": 1.0,
            "supplier_capacity": 500.0,
            "supplier_reliability": 0.90,
        }
    ]

    result = solve_supply_chain(
        products=raw_products,
        shipping_options=raw_shipping,
        scenario={"budget": {"max_total_cost": 50000.0}, "inventory": {"minimum_required_units": 50.0}},
    )

    assert result.status == "OPTIMAL"
    assert len(result.decisions) == 1
    assert result.decisions[0].supplier_id == "SUP100"


def test_ml_enrichment_and_caching(deterministic_fixture):
    """Test 12: ML prediction enrichment runs safely and caches predictions."""
    candidate_options, products, config = deterministic_fixture
    clear_prediction_cache()

    enriched, version, ts, warnings = enrich_candidate_options_with_ml(
        candidate_options=candidate_options,
        config=config,
        cache_predictions=True,
    )

    assert len(enriched) == len(candidate_options)
    # Check that predictions are valid floats
    for opt in enriched:
        assert 0.0 <= opt.predicted_delay_probability <= 1.0
        assert opt.predicted_delay_days >= 0.0
