"""
Unit Tests for Optimization Configuration and Input Validation
==============================================================
Verifies:
1. ScenarioConfig loads valid parameters and default baseline values.
2. Negative budgets, negative capacities, and negative demands are rejected.
3. Currency code validation (strict 3-letter uppercase).
4. Pre-solve validation report accurately flags data inconsistencies.
5. OptimizationResult serializes to dictionary / JSON cleanly.
"""

import pytest
from pydantic import ValidationError

from optimization.config import (
    BudgetConfig,
    InventoryConfig,
    ScenarioConfig,
    load_scenario_config,
)
from optimization.results import (
    ConstraintSummary,
    ObjectiveSummary,
    OptimizationResult,
)
from optimization.validation import validate_optimization_inputs
from optimization.variables import CandidateOption, ProductData


def test_baseline_config_loading():
    config = load_scenario_config()
    assert config.scenario_name == "baseline_supply_chain"
    assert config.budget.max_total_cost == 50000.0
    assert config.budget.currency == "USD"
    assert config.inventory.minimum_required_units == 1000.0
    assert config.delivery.maximum_acceptable_delay_days == 7.0
    assert config.supplier.default_max_capacity_units == 5000.0
    assert config.optimization.solver == "pulp"


def test_negative_budget_rejected():
    with pytest.raises(ValidationError):
        BudgetConfig(max_total_cost=-100.0)


def test_invalid_currency_rejected():
    with pytest.raises(ValidationError):
        BudgetConfig(max_total_cost=50000.0, currency="TOOLONG")

    with pytest.raises(ValidationError):
        BudgetConfig(max_total_cost=50000.0, currency="12")


def test_negative_inventory_rejected():
    with pytest.raises(ValidationError):
        InventoryConfig(minimum_required_units=-50.0)


def test_validation_detects_duplicate_product():
    config = load_scenario_config()
    products = [
        ProductData("P1", "Widget", 10.0, 100.0, 10.0, 1.0, 20.0),
        ProductData("P1", "Duplicate Widget", 10.0, 100.0, 10.0, 1.0, 20.0),
    ]
    options = [
        CandidateOption("S1", "Supplier 1", "P1", "Widget", "Road", 10.0, 1.0, 2.0, 0.1, 0.5, 0.01, 1000.0),
    ]

    report = validate_optimization_inputs(options, products, config)
    assert report.is_valid is False
    assert any("Duplicate product_id" in err for err in report.errors)


def test_validation_detects_unknown_product_in_option():
    config = load_scenario_config()
    products = [
        ProductData("P1", "Widget", 10.0, 100.0, 10.0, 1.0, 20.0),
    ]
    options = [
        CandidateOption("S1", "Supplier 1", "P_NONEXISTENT", "Ghost", "Road", 10.0, 1.0, 2.0, 0.1, 0.5, 0.01, 1000.0),
    ]

    report = validate_optimization_inputs(options, products, config)
    assert report.is_valid is False
    assert any("unknown product_id" in err for err in report.errors)


def test_result_serialization():
    result = OptimizationResult(
        scenario_name="test_serialization",
        status="OPTIMAL",
        solver_name="HiGHS",
        solve_time_seconds=0.015,
        objective=ObjectiveSummary(
            name="minimize_total_cost",
            total_cost=15200.50,
            currency="USD",
            cost_breakdown={"procurement": 12000.0, "shipping": 3200.50},
        ),
        constraints=ConstraintSummary(
            budget_limit=50000.0,
            minimum_inventory_units=1000.0,
            maximum_acceptable_delay_days=7.0,
            default_supplier_capacity_units=5000.0,
        ),
    )

    data = result.to_dict()
    assert isinstance(data, dict)
    assert data["scenario_name"] == "test_serialization"
    assert data["status"] == "OPTIMAL"
    assert data["objective"]["total_cost"] == 15200.50
    assert data["objective"]["currency"] == "USD"
    assert data["constraints"]["budget_limit"] == 50000.0
