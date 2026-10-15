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
    RiskConfig,
    ScenarioConfig,
    SolverConfig,
    SupplierConfig,
    get_baseline_scenario,
    load_scenario_config,
)

logger = logging.getLogger("optimization.scenarios")


def get_budget_constrained_scenario(
    budget: Optional[float] = None,
    budget_multiplier: float = 0.6,
) -> ScenarioConfig:
    """
    Scenario B — Budget-Constrained
    Evaluates supply-chain allocations under restricted cash liquidity.
    Enforces required inventory buffers and demand fulfillment to determine
    whether a feasible plan exists within the curtailed budget.
    """
    baseline = get_baseline_scenario()
    new_budget = float(budget) if budget is not None else round(baseline.budget.max_total_cost * budget_multiplier, 2)
    return ScenarioConfig(
        scenario_name="budget_constrained",
        description=f"Liquidity-constrained scenario with budget capped at {new_budget:,.2f} USD ({budget_multiplier * 100:.0f}% of baseline)",
        budget=BudgetConfig(max_total_cost=new_budget, currency=baseline.budget.currency),
        inventory=baseline.inventory,
        delivery=baseline.delivery,
        supplier=baseline.supplier,
        risk=baseline.risk,
        optimization=baseline.optimization,
    )


def get_delay_sensitive_scenario(
    max_delay_days: float = 3.0,
    daily_delay_penalty: float = 100.0,
) -> ScenarioConfig:
    """
    Scenario C — Delay-Sensitive
    Applies a significantly higher late-delivery penalty and tighter acceptable delay bound.
    Directs the solver toward faster transport modes and lower-delay suppliers.
    """
    baseline = get_baseline_scenario()
    return ScenarioConfig(
        scenario_name="delay_sensitive",
        description=f"Delay-sensitive scenario with penalty increased to {daily_delay_penalty:,.2f} $/day and delay capped at {max_delay_days:.1f} days",
        budget=BudgetConfig(max_total_cost=75000.0, currency=baseline.budget.currency),
        inventory=baseline.inventory,
        delivery=DeliveryConfig(
            maximum_acceptable_delay_days=max_delay_days,
            daily_delay_penalty=daily_delay_penalty,
        ),
        supplier=baseline.supplier,
        risk=baseline.risk,
        optimization=baseline.optimization,
    )


def get_risk_averse_scenario(
    operational_risk_cost_rate: float = 25.0,
) -> ScenarioConfig:
    """
    Scenario D — Risk-Averse
    Applies an explicit operational risk cost based on supplier unreliability (1 - reliability).
    Prioritizes highly reliable suppliers when historical supplier data supports the distinction.
    """
    baseline = get_baseline_scenario()
    return ScenarioConfig(
        scenario_name="risk_averse",
        description=f"Risk-averse scenario with operational risk penalty of {operational_risk_cost_rate:,.2f} $/unit on supplier unreliability",
        budget=BudgetConfig(max_total_cost=80000.0, currency=baseline.budget.currency),
        inventory=baseline.inventory,
        delivery=baseline.delivery,
        supplier=baseline.supplier,
        risk=RiskConfig(operational_risk_cost_rate=operational_risk_cost_rate, enabled=True),
        optimization=baseline.optimization,
    )


def get_expedited_service_scenario(max_delay_days: float = 2.0) -> ScenarioConfig:
    """
    High-service-level scenario strictly prohibiting delay-prone routes.
    Forces optimizer to prioritize reliable suppliers and faster transit modes.
    """
    return get_delay_sensitive_scenario(max_delay_days=max_delay_days, daily_delay_penalty=50.0)


def get_inventory_buffering_scenario(min_inventory_units: float = 2500.0) -> ScenarioConfig:
    """
    Supply-chain resilience scenario maintaining high safety stock to protect against
    upstream disruption.
    """
    baseline = get_baseline_scenario()
    return ScenarioConfig(
        scenario_name="inventory_buffering",
        description=f"Resilience buffering scenario requiring minimum ending inventory of {min_inventory_units:,.0f} units",
        budget=BudgetConfig(max_total_cost=100000.0, currency=baseline.budget.currency),
        inventory=InventoryConfig(
            minimum_required_units=min_inventory_units,
            holding_cost_rate=0.05,
            shortage_penalty_rate=2.0,
        ),
        delivery=baseline.delivery,
        supplier=baseline.supplier,
        risk=baseline.risk,
        optimization=baseline.optimization,
    )


SCENARIO_REGISTRY = {
    "baseline": get_baseline_scenario,
    "baseline_supply_chain": get_baseline_scenario,
    "budget_constrained": get_budget_constrained_scenario,
    "delay_sensitive": get_delay_sensitive_scenario,
    "risk_averse": get_risk_averse_scenario,
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
    return load_scenario_config(overrides=overrides or {"scenario_name": name})


def compare_scenarios(
    baseline_result: Any,
    counterfactual_result: Any,
) -> Dict[str, Any]:
    """
    Compare a counterfactual scenario result against the baseline result.
    Computes delta in objective value, cost breakdowns, allocations, and constraints.
    """
    base_obj = baseline_result.objective_value if hasattr(baseline_result, "objective_value") else getattr(baseline_result.objective, "total_cost", None)
    cf_obj = counterfactual_result.objective_value if hasattr(counterfactual_result, "objective_value") else getattr(counterfactual_result.objective, "total_cost", None)

    obj_diff = None
    obj_pct_change = None
    if base_obj is not None and cf_obj is not None:
        obj_diff = round(cf_obj - base_obj, 2)
        obj_pct_change = round((obj_diff / base_obj * 100.0), 2) if base_obj > 0 else 0.0

    # Breakdown diff
    base_cb = baseline_result.cost_breakdown or {}
    cf_cb = counterfactual_result.cost_breakdown or {}
    cost_diffs: Dict[str, Optional[float]] = {}
    all_keys = set(base_cb.keys()).union(cf_cb.keys())
    for k in sorted(all_keys):
        v_base = base_cb.get(k)
        v_cf = cf_cb.get(k)
        if v_base is not None and v_cf is not None:
            cost_diffs[k] = round(v_cf - v_base, 2)
        else:
            cost_diffs[k] = None

    # Decision allocation shift
    base_qty_by_sup: Dict[str, float] = {}
    for d in getattr(baseline_result, "decisions", []):
        base_qty_by_sup[d.supplier_id] = base_qty_by_sup.get(d.supplier_id, 0.0) + d.quantity

    cf_qty_by_sup: Dict[str, float] = {}
    for d in getattr(counterfactual_result, "decisions", []):
        cf_qty_by_sup[d.supplier_id] = cf_qty_by_sup.get(d.supplier_id, 0.0) + d.quantity

    supplier_shift = {}
    all_sups = set(base_qty_by_sup.keys()).union(cf_qty_by_sup.keys())
    for s in sorted(all_sups):
        q_base = base_qty_by_sup.get(s, 0.0)
        q_cf = cf_qty_by_sup.get(s, 0.0)
        supplier_shift[s] = round(q_cf - q_base, 2)

    return {
        "baseline_scenario_id": getattr(baseline_result, "scenario_id", getattr(baseline_result, "scenario_name", "baseline")),
        "counterfactual_scenario_id": getattr(counterfactual_result, "scenario_id", getattr(counterfactual_result, "scenario_name", "counterfactual")),
        "baseline_status": baseline_result.status,
        "counterfactual_status": counterfactual_result.status,
        "objective_baseline": base_obj,
        "objective_counterfactual": cf_obj,
        "objective_difference": obj_diff,
        "objective_percent_change": obj_pct_change,
        "cost_breakdown_differences": cost_diffs,
        "supplier_allocation_shifts": supplier_shift,
    }
