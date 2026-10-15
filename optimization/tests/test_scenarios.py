"""
Unit Tests for SupplyPrescript Scenario Management (Day 12)
===========================================================
Verifies:
1. Scenario A — Baseline scenario configuration and execution.
2. Scenario B — Budget-Constrained scenario and liquidity stress testing.
3. Scenario C — Delay-Sensitive scenario preferring lower-delay options.
4. Scenario D — Risk-Averse scenario prioritizing reliable suppliers.
5. Scenario comparison and difference reporting.
6. Scenario registry and parameter overrides.
"""

import pytest

from optimization.scenarios import (
    compare_scenarios,
    create_scenario,
    get_baseline_scenario,
    get_budget_constrained_scenario,
    get_delay_sensitive_scenario,
    get_risk_averse_scenario,
    list_available_scenarios,
)
from optimization.solver import solve_supply_chain
from optimization.variables import CandidateOption, ProductData


@pytest.fixture
def scenario_fixture():
    products = [
        ProductData(
            product_id="P1",
            product_name="Product Alpha",
            starting_inventory=50.0,
            demand=100.0,
            unit_cost=30.0,
            holding_cost_per_unit=1.5,
            shortage_penalty_per_unit=45.0,
        ),
    ]

    # Two suppliers for P1:
    # S1: Cheap ($30), high delay (2.5 days), lower reliability (0.75)
    # S2: Slightly more expensive ($35), low delay (0.4 days), high reliability (0.98)
    candidate_options = [
        CandidateOption(
            supplier_id="S1_RISKY_CHEAP",
            supplier_name="Cheap Risky Supplier",
            product_id="P1",
            product_name="Product Alpha",
            transport_mode="Road",
            unit_cost=30.0,
            shipping_cost_per_unit=3.0,
            lead_time_days=6.0,
            predicted_delay_probability=0.40,
            predicted_delay_days=2.5,
            expected_delay_cost_per_unit=0.25,
            supplier_capacity=1000.0,
            supplier_reliability=0.75,
            expected_risk_cost_per_unit=0.0,
        ),
        CandidateOption(
            supplier_id="S2_SAFE_EXPENSIVE",
            supplier_name="Safe Reliable Supplier",
            product_id="P1",
            product_name="Product Alpha",
            transport_mode="Air",
            unit_cost=35.0,
            shipping_cost_per_unit=5.0,
            lead_time_days=1.5,
            predicted_delay_probability=0.05,
            predicted_delay_days=0.4,
            expected_delay_cost_per_unit=0.01,
            supplier_capacity=1000.0,
            supplier_reliability=0.98,
            expected_risk_cost_per_unit=0.0,
        ),
    ]

    return candidate_options, products


def test_baseline_scenario_solves(scenario_fixture):
    """Scenario A: Baseline solves with expected defaults."""
    candidate_options, products = scenario_fixture
    baseline_cfg = get_baseline_scenario()
    baseline_cfg.inventory.minimum_required_units = 100.0

    result = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=baseline_cfg)

    assert result.status == "OPTIMAL"
    assert result.scenario_id in ("baseline", "baseline_supply_chain")
    # Baseline with no risk penalty prefers the cheaper supplier S1
    s1_dec = [d for d in result.decisions if d.supplier_id == "S1_RISKY_CHEAP"]
    assert len(s1_dec) > 0


def test_budget_constrained_scenario_behavior(scenario_fixture):
    """Scenario B: Budget-constrained scenario detects feasibility threshold."""
    candidate_options, products = scenario_fixture

    # Test feasible tighter budget
    tight_cfg = get_budget_constrained_scenario(budget=8000.0)
    tight_cfg.inventory.minimum_required_units = 100.0
    res_tight = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=tight_cfg)
    assert res_tight.status == "OPTIMAL"

    # Test infeasible budget: $500 cannot fulfill 150 net units (unit cost $30 -> min $4500)
    stress_cfg = get_budget_constrained_scenario(budget=500.0)
    stress_cfg.inventory.minimum_required_units = 100.0
    stress_cfg.optimization.allow_shortage = False

    res_stress = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=stress_cfg)
    assert res_stress.status == "INFEASIBLE"
    assert res_stress.infeasibility_diagnostics is not None
    assert any("budget" in c.lower() for c in res_stress.infeasibility_diagnostics.conflicting_constraints)


def test_delay_sensitive_scenario_shifts_allocation(scenario_fixture):
    """Scenario C: Higher delay penalty and tighter delay limit shifts allocation to low-delay options."""
    candidate_options, products = scenario_fixture

    # Tighter delay threshold (1.0 day max) eliminates S1 (predicted delay 2.5d)
    delay_cfg = get_delay_sensitive_scenario(max_delay_days=1.0, daily_delay_penalty=200.0)
    delay_cfg.inventory.minimum_required_units = 100.0

    result = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=delay_cfg)

    assert result.status == "OPTIMAL"
    # S1 prohibited due to delay > 1.0 day, S2 must be chosen exclusively
    assert all(d.supplier_id == "S2_SAFE_EXPENSIVE" for d in result.decisions)


def test_risk_averse_scenario_favors_reliable_suppliers(scenario_fixture):
    """Scenario D: Operational risk cost penalizes unreliable suppliers, shifting to reliable supplier."""
    candidate_options, products = scenario_fixture

    # High operational risk penalty ($40/unit unreliability)
    # S1 unreliability = 0.25 -> $10.00 risk cost per unit (total $30 + $3 + $0.25 + $10 = $43.25)
    # S2 unreliability = 0.02 -> $0.80 risk cost per unit (total $35 + $5 + $0.01 + $0.80 = $40.81)
    risk_cfg = get_risk_averse_scenario(operational_risk_cost_rate=40.0)
    risk_cfg.inventory.minimum_required_units = 100.0

    result = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=risk_cfg)

    assert result.status == "OPTIMAL"
    # S2 is now cheaper overall when operational risk is monetized
    assert any(d.supplier_id == "S2_SAFE_EXPENSIVE" for d in result.decisions)
    assert result.cost_breakdown["risk_cost"] > 0


def test_scenario_comparison_utility(scenario_fixture):
    """Test scenario diff utility compares baseline vs counterfactual correctly."""
    candidate_options, products = scenario_fixture
    baseline_cfg = get_baseline_scenario()
    baseline_cfg.inventory.minimum_required_units = 100.0
    base_res = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=baseline_cfg)

    risk_cfg = get_risk_averse_scenario(operational_risk_cost_rate=40.0)
    risk_cfg.inventory.minimum_required_units = 100.0
    cf_res = solve_supply_chain(candidate_options=candidate_options, product_data=products, scenario=risk_cfg)

    diff = compare_scenarios(base_res, cf_res)
    assert diff["baseline_status"] == "OPTIMAL"
    assert diff["counterfactual_status"] == "OPTIMAL"
    assert diff["objective_difference"] is not None
    assert "cost_breakdown_differences" in diff
    assert "supplier_allocation_shifts" in diff


def test_scenario_registry_and_overrides():
    """Test registry retrieval and custom scenario overrides."""
    scenarios = list_available_scenarios()
    assert "baseline" in scenarios
    assert "budget_constrained" in scenarios
    assert "delay_sensitive" in scenarios
    assert "risk_averse" in scenarios

    custom = create_scenario("baseline", overrides={"budget": {"max_total_cost": 33000.0}})
    assert custom.budget.max_total_cost == 33000.0
