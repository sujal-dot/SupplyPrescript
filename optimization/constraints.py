"""
SupplyPrescript — Optimization Constraints Module
=================================================
Formulates and applies all mathematical business constraints using PuLP:

1. Budget Constraint:
   C_procurement + C_shipping + C_holding + C_delay <= max_total_cost

2. Minimum Inventory Constraint:
   sum_p I_p >= minimum_required_units (and optional per-product bounds)

3. Inventory Balance Constraint:
   sum_{s, m} q_{s, p, m} - I_p + u_p = demand_p - I_p^{starting}  (for all p)

4. Maximum Acceptable Delay Constraint:
   q_{s, p, m} == 0 for options where predicted_delay_days > maximum_acceptable_delay_days
   (or total delivery time > max_lead_time_days)

5. Supplier Capacity Constraint:
   sum_{p, m} q_{s, p, m} <= capacity_s  (for all s)

6. Demand Fulfillment & Shortage Bounds:
   u_p <= demand_p (or u_p == 0 if allow_shortage is False)

7. Non-Negativity and Integrity:
   q >= 0, I >= 0, u >= 0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pulp

from optimization.config import ScenarioConfig
from optimization.objective import ObjectiveExpressions
from optimization.variables import CandidateOption, OptimizationVariables, ProductData

logger = logging.getLogger("optimization.constraints")


@dataclass
class AppliedConstraint:
    """Metadata tracking an applied constraint for slack and post-solve auditing."""
    name: str
    category: str
    expression: pulp.LpConstraint
    rhs: float
    description: str


@dataclass
class ConstraintRegistry:
    """Registry of all constraints added to the optimization model."""
    constraints: List[AppliedConstraint] = field(default_factory=list)
    delay_pruned_options: List[str] = field(default_factory=list)

    def get_by_category(self, category: str) -> List[AppliedConstraint]:
        return [c for c in self.constraints if c.category == category]


def apply_business_constraints(
    problem: pulp.LpProblem,
    variables: OptimizationVariables,
    objectives: ObjectiveExpressions,
    candidate_options: List[CandidateOption],
    products: List[ProductData],
    config: ScenarioConfig,
) -> ConstraintRegistry:
    """
    Formulate and register all operational business constraints into the PuLP problem.
    """
    registry = ConstraintRegistry()
    products_by_id = {prod.product_id: prod for prod in products}

    # -------------------------------------------------------------------------
    # 1. Budget Constraint
    # -------------------------------------------------------------------------
    # Cash expenditure (procurement + shipping + holding + delay) <= budget
    budget_limit = float(config.budget.max_total_cost)
    budget_c = objectives.cash_expenditure <= budget_limit
    problem += budget_c, "Constraint_Budget_Limit"
    registry.constraints.append(
        AppliedConstraint(
            name="Constraint_Budget_Limit",
            category="Budget",
            expression=budget_c,
            rhs=budget_limit,
            description=f"Total supply-chain expenditure must not exceed {budget_limit:.2f} {config.budget.currency}",
        )
    )

    # -------------------------------------------------------------------------
    # 2. Inventory Balance Constraints (per product)
    # -------------------------------------------------------------------------
    # sum_{s, m} q[s, p, m] - I[p] + u[p] == demand[p] - starting_inventory[p]
    for prod in products:
        p_id = prod.product_id
        procured_expr = variables.get_procured_for_product(p_id)
        ending_inv_var = variables.I[p_id]
        shortage_var = variables.u[p_id]

        net_requirement = float(prod.demand - prod.starting_inventory)
        balance_c = (procured_expr - ending_inv_var + shortage_var == net_requirement)
        c_name = f"Constraint_Inventory_Balance_{p_id}".replace("-", "_")
        problem += balance_c, c_name
        registry.constraints.append(
            AppliedConstraint(
                name=c_name,
                category="InventoryBalance",
                expression=balance_c,
                rhs=net_requirement,
                description=f"Inventory flow conservation for product {prod.product_name} ({p_id})",
            )
        )

    # -------------------------------------------------------------------------
    # 3. Minimum Inventory Constraint (Aggregate & Per-Product)
    # -------------------------------------------------------------------------
    # Aggregate: sum_p I[p] >= minimum_required_units
    min_inv_units = float(config.inventory.minimum_required_units)
    if min_inv_units > 0:
        total_ending_inventory = pulp.lpSum(list(variables.I.values()))
        min_inv_c = total_ending_inventory >= min_inv_units
        problem += min_inv_c, "Constraint_Minimum_Inventory_Aggregate"
        registry.constraints.append(
            AppliedConstraint(
                name="Constraint_Minimum_Inventory_Aggregate",
                category="MinimumInventory",
                expression=min_inv_c,
                rhs=min_inv_units,
                description=f"Aggregate ending inventory must be at least {min_inv_units:.1f} units",
            )
        )

    # Per-product minimum if explicitly requested on ProductData
    for prod in products:
        if prod.minimum_inventory > 0:
            p_id = prod.product_id
            prod_min_c = variables.I[p_id] >= float(prod.minimum_inventory)
            c_name = f"Constraint_Minimum_Inventory_{p_id}".replace("-", "_")
            problem += prod_min_c, c_name
            registry.constraints.append(
                AppliedConstraint(
                    name=c_name,
                    category="MinimumInventory",
                    expression=prod_min_c,
                    rhs=float(prod.minimum_inventory),
                    description=f"Minimum ending buffer for product {prod.product_name} ({p_id}) >= {prod.minimum_inventory}",
                )
            )

    # -------------------------------------------------------------------------
    # 4. Supplier Capacity Constraints (per supplier)
    # -------------------------------------------------------------------------
    # sum_{p, m} q[s, p, m] <= capacity[s]
    supplier_capacities: Dict[str, float] = {}
    for opt in candidate_options:
        if opt.supplier_id not in supplier_capacities:
            cap = (
                opt.supplier_capacity
                if config.supplier.use_individual_capacities and opt.supplier_capacity > 0
                else config.supplier.default_max_capacity_units
            )
            supplier_capacities[opt.supplier_id] = float(cap)

    for s_id in variables.supplier_ids:
        cap_val = supplier_capacities.get(s_id, config.supplier.default_max_capacity_units)
        supplier_procured_expr = variables.get_procured_from_supplier(s_id)

        # Apply constraint only if supplier has candidate variables
        if not isinstance(supplier_procured_expr, (int, float)):
            cap_c = supplier_procured_expr <= cap_val
            c_name = f"Constraint_Supplier_Capacity_{s_id}".replace("-", "_")
            problem += cap_c, c_name
            registry.constraints.append(
                AppliedConstraint(
                    name=c_name,
                    category="SupplierCapacity",
                    expression=cap_c,
                    rhs=cap_val,
                    description=f"Supplier {s_id} procurement limit <= {cap_val:.1f} units",
                )
            )

    # -------------------------------------------------------------------------
    # 5. Maximum Acceptable Delay / Delivery Deadline Constraints
    # -------------------------------------------------------------------------
    # For any route/option exceeding maximum acceptable delay, set q == 0
    max_delay = float(config.delivery.maximum_acceptable_delay_days)
    max_total_time = config.delivery.max_total_lead_time_days

    for opt in candidate_options:
        key = (opt.supplier_id, opt.product_id, opt.transport_mode)
        var = variables.q.get(key)
        if var is None:
            continue

        is_delay_violation = opt.predicted_delay_days > max_delay
        is_total_time_violation = (
            max_total_time is not None
            and (opt.lead_time_days + opt.predicted_delay_days) > max_total_time
        )

        if is_delay_violation or is_total_time_violation:
            reason = (
                f"predicted delay ({opt.predicted_delay_days:.1f}d > {max_delay:.1f}d)"
                if is_delay_violation
                else f"total transit time ({opt.lead_time_days + opt.predicted_delay_days:.1f}d > {max_total_time}d)"
            )
            delay_c = var == 0
            c_name = f"Constraint_Max_Delay_Prohibit_{opt.supplier_id}_{opt.product_id}_{opt.transport_mode}".replace("-", "_").replace(" ", "_")
            problem += delay_c, c_name
            registry.constraints.append(
                AppliedConstraint(
                    name=c_name,
                    category="DeliveryDeadline",
                    expression=delay_c,
                    rhs=0.0,
                    description=f"Option {key} prohibited due to {reason}",
                )
            )
            registry.delay_pruned_options.append(f"{opt.supplier_id}-{opt.product_id}-{opt.transport_mode}: {reason}")

    # -------------------------------------------------------------------------
    # 6. Demand Fulfillment / Shortage Limits
    # -------------------------------------------------------------------------
    for prod in products:
        p_id = prod.product_id
        shortage_var = variables.u[p_id]
        if not config.optimization.allow_shortage:
            shortage_zero_c = shortage_var == 0
            c_name = f"Constraint_Strict_Demand_Fulfillment_{p_id}".replace("-", "_")
            problem += shortage_zero_c, c_name
            registry.constraints.append(
                AppliedConstraint(
                    name=c_name,
                    category="DemandFulfillment",
                    expression=shortage_zero_c,
                    rhs=0.0,
                    description=f"Strict fulfillment required for {prod.product_name} ({p_id}); zero shortage permitted",
                )
            )

    logger.debug("Applied %d mathematical constraints to optimization problem.", len(registry.constraints))
    return registry
