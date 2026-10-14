"""
SupplyPrescript — Scenario Configuration System
===============================================
Defines standard planning scenarios and programmatic alternative scenario generators.
Enables sensitivity analysis, counterfactual what-if simulations, and stress testing.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from optimization.config import (
    BudgetConfig,
    DeliveryConfig,
    InventoryConfig,
    ScenarioConfig,
    SolverConfig,
    SupplierConfig,
    get_baseline_scenario,
    load_scenario_config,
)

logger = logging.getLogger("optimization.scenarios")


def get_budget_constrained_scenario(budget_multiplier: float = 0.6) -> ScenarioConfig:
    """
    Budget-stressed scenario evaluating procurement trade-offs and possible shortages
    under restricted liquidity.
    """
    baseline = get_baseline_scenario()
    new_budget = round(baseline.budget.max_total_cost * budget_multiplier, 2)
    return ScenarioConfig(
        scenario_name="budget_constrained_stress_test",
        description=f"Austerity scenario with budget capped at {budget_multiplier * 100:.0f}% of baseline ({new_budget:,.2f} USD)",
        budget=BudgetConfig(max_total_cost=new_budget, currency="USD"),
        inventory=baseline.inventory,
        delivery=baseline.delivery,
        supplier=baseline.supplier,
        optimization=baseline.optimization,
    )


def get_expedited_service_scenario(max_delay_days: float = 2.0) -> ScenarioConfig:
    """
    High-service-level scenario strictly prohibiting delay-prone routes.
    Forces optimizer to prioritize reliable suppliers and faster transit modes.
    """
    baseline = get_baseline_scenario()
    return ScenarioConfig(
        scenario_name="high_service_expedited_transit",
        description=f"Zero-tolerance service level capping predicted delay at {max_delay_days:.1f} days",
        budget=BudgetConfig(max_total_cost=75000.0, currency="USD"),  # Higher budget to accommodate air freight
        inventory=baseline.inventory,
        delivery=DeliveryConfig(maximum_acceptable_delay_days=max_delay_days, daily_delay_penalty=50.0),
        supplier=baseline.supplier,
        optimization=baseline.optimization,
    )


def get_inventory_buffering_scenario(min_inventory_units: float = 2500.0) -> ScenarioConfig:
    """
    Supply-chain resilience scenario maintaining high safety stock to protect against
    upstream disruption.
    """
    baseline = get_baseline_scenario()
    return ScenarioConfig(
        scenario_name="inventory_buffering_resilience",
        description=f"Resilience buffering scenario requiring minimum ending inventory of {min_inventory_units:,.0f} units",
        budget=BudgetConfig(max_total_cost=100000.0, currency="USD"),
        inventory=InventoryConfig(
            minimum_required_units=min_inventory_units,
            holding_cost_rate=0.05,
            shortage_penalty_rate=2.0,
        ),
        delivery=baseline.delivery,
        supplier=baseline.supplier,
        optimization=baseline.optimization,
    )


SCENARIO_REGISTRY = {
    "baseline_supply_chain": get_baseline_scenario,
    "budget_constrained": get_budget_constrained_scenario,
    "high_service_expedited": get_expedited_service_scenario,
    "inventory_buffering": get_inventory_buffering_scenario,
}


def list_available_scenarios() -> List[str]:
    """Returns list of registered standard scenario identifiers."""
    return list(SCENARIO_REGISTRY.keys())


def create_scenario(name: str, overrides: Optional[Dict[str, Any]] = None) -> ScenarioConfig:
    """
    Factory creating a scenario by name with optional overrides.
    """
    factory = SCENARIO_REGISTRY.get(name)
    if factory:
        base_scenario = factory()
        if overrides:
            return load_scenario_config(overrides=overrides)
        return base_scenario
    # If not predefined, load baseline and apply overrides
    return load_scenario_config(overrides=overrides or {"scenario_name": name})
